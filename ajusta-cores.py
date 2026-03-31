#!/usr/bin/env python3
# :tabSize=4:indentSize=4:noTabs=true:

import gi
gi.require_version('Gimp', '3.0')
gi.require_version('Gtk', '3.0')

import sys, os
from gi.repository import Gimp, GObject, GLib, Gio, Gtk, Gegl

def escolher_pasta(titulo):
    dialog = Gtk.FileChooserDialog( title=titulo, action=Gtk.FileChooserAction.SELECT_FOLDER )
    dialog.add_buttons( Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OK, Gtk.ResponseType.OK )

    folder = None
    if dialog.run() == Gtk.ResponseType.OK:
        folder = dialog.get_filename()

    dialog.destroy()
    return folder


def run(procedure, run_mode, image, drawables, config, data):

    entrada = escolher_pasta("Selecione a pasta de entrada")
    if not entrada:
        return procedure.new_return_values(Gimp.PDBStatusType.CANCEL, GLib.Error())

    saida = escolher_pasta("Selecione a pasta de saída")
    if not saida:
        return procedure.new_return_values(Gimp.PDBStatusType.CANCEL, GLib.Error())

    if not os.path.exists(saida):
        os.makedirs(saida)

    arquivos = [
        f for f in os.listdir(entrada)
        if f.lower().endswith((".jpg", ".jpeg"))
    ]

    for nome in arquivos:
        caminho_entrada = os.path.join(entrada, nome)
        caminho_saida = os.path.join(saida, nome)

        try:
            print(f"Processando: {nome}")

            img = Gimp.file_load(run_mode, Gio.File.new_for_path(caminho_entrada))

            layers = img.get_layers()
            if not layers:
                img.delete()
                continue
            drawable = layers[0]

            #----------------------------------------------------------------------------------------------------------
            #https://discourse.gnome.org/t/issues-porting-a-curve-script-to-gimp-3/28305
            drawable.curves_spline(Gimp.HistogramChannel.VALUE,[
                0  /255 , 5 / 255,
                241/255 , 223/255,
                234/255 , 222/255,
                255/255 , 248/255
            ])

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

            #----------------------------------------------------------------------------------------------------------

            # Salvar imagem
            pdb = Gimp.get_pdb()
            proc = pdb.lookup_procedure("file-jpeg-export")
            config = proc.create_config()
            config.set_property("run-mode", Gimp.RunMode.NONINTERACTIVE)
            config.set_property("image", img)
            config.set_property("file", Gio.File.new_for_path(caminho_saida))
            config.set_property("quality", 0.95)
            proc.run(config)

            # Apagar a imagem atual da memoria
            img.delete()

        except Exception as e:
            print(f"Erro em {nome}: {e}")

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
