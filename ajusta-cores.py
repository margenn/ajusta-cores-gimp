#!/usr/bin/env python3
# :tabSize=4:indentSize=4:noTabs=true:

import sys, os, gi, struct
gi.require_version('Gimp', '3.0')
gi.require_version('Gtk', '3.0')
gi.require_version("Gegl", "0.4")
from gi.repository import Gimp, GObject, GLib, Gio, Gtk, Gegl

def apply_levels(drawable, black, white, gamma):
    from gi.repository import Gimp
    pdb = Gimp.get_pdb()
    proc = pdb.lookup_procedure("gimp-drawable-levels")
    config = proc.create_config()
    config.set_property("drawable", drawable)
    config.set_property("channel", Gimp.HistogramChannel.VALUE)
    # ✅ tudo em 0–1
    config.set_property("low-input", black)
    config.set_property("high-input", white)
    config.set_property("gamma", gamma)
    config.set_property("low-output", 0.0)
    config.set_property("high-output", 1.0)
    proc.run(config)
    return None

def histogram_compute(drawable):
    buffer = drawable.get_buffer()
    rect = buffer.get_extent()
    width = rect.width
    height = rect.height
    hist = [0] * 256
    data = buffer.get( rect, 1.0, "RGBA float", 0 )
    num_pixels = width * height
    for i in range(num_pixels):
        r, g, b, a = struct.unpack_from("ffff", data, i * 16)
        #lum = 0.2126*r + 0.7152*g + 0.0722*b
        lum = max(r, g, b)
        idx = int(lum * 255)
        idx = max(0, min(255, idx))
        hist[idx] += 1
    return hist

def escolher_pasta(titulo):
    dialog = Gtk.FileChooserDialog( title=titulo, action=Gtk.FileChooserAction.SELECT_FOLDER )
    dialog.add_buttons( Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OK, Gtk.ResponseType.OK )
    folder = None
    if dialog.run() == Gtk.ResponseType.OK:
        folder = dialog.get_filename()
    dialog.destroy()
    return folder

def fill_zeros_nearest(hist):
    hist = hist.copy()
    n = len(hist)
    for i in range(n):
        if hist[i] == 0:
            left = None
            right = None
            # procura à esquerda
            for j in range(i - 1, -1, -1):
                if hist[j] != 0:
                    left = j
                    break
            # procura à direita
            for j in range(i + 1, n):
                if hist[j] != 0:
                    right = j
                    break
            # decide o mais próximo
            if left is None:
                hist[i] = hist[right]
            elif right is None:
                hist[i] = hist[left]
            else:
                if (i - left) <= (right - i):
                    hist[i] = hist[left]
                else:
                    hist[i] = hist[right]
    return hist

def histogram_edges(hist, threshold_ratio=0.005):
    peak = max(hist)
    threshold = peak * threshold_ratio
    black = 0
    for i in range(1, 256):
        if ( hist[i] > threshold and hist[i] > hist[i-1] ):
            black = i
            break
    white = 255
    for i in range(254, -1, -1):
        if ( hist[i] > threshold and hist[i] > hist[i+1] ):
            white = i
            break
    return black/255.0, white/255.0

def salva_imagem(img, caminho_saida):
    # Salvar imagem
    pdb = Gimp.get_pdb()
    proc = pdb.lookup_procedure("file-jpeg-export")
    config = proc.create_config()
    config.set_property("run-mode", Gimp.RunMode.NONINTERACTIVE)
    config.set_property("image", img)
    config.set_property("file", Gio.File.new_for_path(caminho_saida))
    config.set_property("quality", 0.95)
    proc.run(config)
    return None

def obter_pastas(debug=False):
    if debug:
        entrada = "/home/ma/Desktop/in"
        saida = "/home/ma/Desktop/out"
    else:
        entrada = escolher_pasta("Selecione a pasta de entrada")
        if not entrada:
            return procedure.new_return_values(Gimp.PDBStatusType.CANCEL, GLib.Error())
        saida = escolher_pasta("Selecione a pasta de saída")
        if not saida:
            return procedure.new_return_values(Gimp.PDBStatusType.CANCEL, GLib.Error())
    os.makedirs(saida, exist_ok=True)
    return entrada, saida

def aumenta_saturacao(drawable):
    # aumenta a saturacao de cores ate o limite, funcionando
    pdb = Gimp.get_pdb()
    proc = pdb.lookup_procedure("gimp-drawable-hue-saturation")
    config = proc.create_config()
    config.set_property("drawable", drawable)
    config.set_property("hue-range", 0)
    config.set_property("hue-offset", 0)
    config.set_property("saturation", 50)
    config.set_property("lightness", 0)
    proc.run(config)
    return None

def estica_histograma(drawable):
    histograma = fill_zeros_nearest(histogram_compute(drawable))
    black, white = histogram_edges(histograma)
    #print(histograma); print(f"black:{black} white:{white}")
    apply_levels(drawable, black, white, 1)
    return None

def run(procedure, run_mode, image, drawables, config, data):
    entrada, saida = obter_pastas()
    arquivosJpg = [ f for f in os.listdir(entrada) if f.lower().endswith((".jpg", ".jpeg")) ]; arquivosJpg.sort()
    total = len(arquivosJpg)
    #for arquivoJpg in arquivosJpg:
    for i, arquivoJpg in enumerate(arquivosJpg):
        progresso = (i + 1) / total * 100; print(f"Processando:{arquivoJpg} ({i+1}/{total}), {progresso:.1f}%")
        caminho_entrada = os.path.join(entrada, arquivoJpg)
        caminho_saida = os.path.join(saida, arquivoJpg)
        try:
            img = Gimp.file_load(run_mode, Gio.File.new_for_path(caminho_entrada))
            layers = img.get_layers()
            if not layers:
                img.delete() # apaga a imagem atual da memoria
                continue # vai para a proximo jpg do loop
            drawable = layers[0]
            estica_histograma(drawable)
            aumenta_saturacao(drawable)
            salva_imagem(img, caminho_saida)
            img.delete() # Apaga a imagem atual da memoria
        except Exception as e:
            print(f"Erro em {arquivoJpg}: {e}")
    return procedure.new_return_values(Gimp.PDBStatusType.SUCCESS, GLib.Error())

class BatchPlugin(Gimp.PlugIn):
    def do_query_procedures(self):
        return ["python-fu-batch-ajusta-cores"]
    def do_create_procedure(self, name):
        procedure = Gimp.ImageProcedure.new( self, name, Gimp.PDBProcType.PLUGIN, run, None )
        procedure.set_menu_label("DRONE AJUSTA CORES")
        procedure.set_image_types("*")
        procedure.set_sensitivity_mask( Gimp.ProcedureSensitivityMask.ALWAYS )
        procedure.add_menu_path("<Image>/Filters")
        return procedure

Gimp.main(BatchPlugin.__gtype__, sys.argv)
