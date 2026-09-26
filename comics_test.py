import comics
import os
os.makedirs(os.path.expanduser("~/.cache/escpos"), exist_ok=True)
os.environ.setdefault("ESCPOS_CAPABILITIES_PICKLE_DIR", os.path.expanduser("~/.cache/escpos"))

from escpos.printer import Usb

ch = comics.search("calvinandhobbes", date="1990-01-02")
ch.download("comic.png")

p = Usb(0x04b8, 0x0e28, 0, profile="TM-T20II")
p.image("./comic.png")
p.cut()
p.close()