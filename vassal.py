import lxml
import lxml.etree
import zipfile
import sys
import os.path
import tempfile

class Piece:
    """Access to a Piece definition of a VASSAL module."""
    def __init__(self, name, width, height, imagename):
        self.name = str(name)
        self.width = str(width)
        self.height = str(height)
        self.imagename = os.path.basename(str(imagename))
        self.backimagename = None
        self.__prototype = None

    def set_prototype(self, prototype):
        self.__prototype = prototype

    def set_back(self, backimagename):
        self.backimagename = os.path.basename(str(backimagename))

    def to_data_sequence(self, quote=''):
        res = []
        pieceimagename = self.imagename
        if self.backimagename:
            pieceimagename = self.backimagename
            res.append(
                'emb2;Flip;2;F;;0;;;0;;;;1;false;0;0;%s;;true;;;;false;;1'
                % self.imagename)
        if self.__prototype:
            res.append("prototype" + ';' + self.__prototype + '\\')
        res.append("piece;;;%s;%s/" % (pieceimagename, self.name))
        res.append("\\")
        res.append("null;0;0")
        return '+/null/' + '\t'.join(res)

#+/null/emb2;Flip;2;F;;0;;;0;;;;1;false;0;0;c_r.png;;true;;;;false;;1       prototype;PPP\  piece;;;e_d.png;FRONT/1;F       \       null;67;39;0

PANELTAGS = [
    "VASSAL.build.widget.PanelWidget",
    ]

PIECESLOTTAG = "VASSAL.build.widget.PieceSlot"

class ModuleFile:
    """Low-level access to VASSAL module (VMOD) files. Very incomplete."""
    def __init__(self, filename):
        self.__filename = filename
        self.__added_images = []
        f = zipfile.ZipFile(filename, "r")
        self.vmodcontents = []
        for i in f.infolist():
            if i.filename == "buildFile":
                buildfile = f.read("buildFile")
                self.__buildfiletree = lxml.etree.fromstring(buildfile)
            else:
                self.vmodcontents.append([i, f.read(i.filename)])
        f.close()

    def __read_buildfile(self, filename):
        return res

    def get_panel(self, entryname=None):
        for e in self.__buildfiletree.iterdescendants():
            if entryname and e.get('entryName') == entryname:
                return e
            elif not entryname and e.tag in PANELTAGS:
                return e

    def add_piece(self, piece, panelname=None):
        panel = self.get_panel(panelname)
        e = lxml.etree.Element(PIECESLOTTAG)
        e.set('entryName', piece.name)
        e.set('width', piece.width)
        e.set('height', piece.height)
        e.text = piece.to_data_sequence()
        panel.append(e)

    def add_imagefile(self, filename):
        self.__added_images.append(filename)

    def save(self):
        f = tempfile.NamedTemporaryFile("w")
        f.write(lxml.etree.tostring(self.__buildfiletree))
        z = zipfile.ZipFile(self.__filename, "w")
        f.flush()
        z.write(f.name, "buildFile")
        f.close()
        for i in self.vmodcontents:
            z.writestr(i[0], i[1])
        for a in self.__added_images:
            arcname = os.path.join("images", os.path.basename(a))
            z.write(a, arcname)
        z.close()

if __name__ == '__main__':
    modfile = ModuleFile(sys.argv[1])
    piecename = sys.argv[2]
    piecewidth = int(sys.argv[3])
    pieceheight = int(sys.argv[4])
    imagename = sys.argv[5]
    imagebackname = sys.argv[6]
    modfile.add_imagefile(imagename)
    modfile.add_imagefile(imagebackname)
    prototypes = sys.argv[7:]
    piece = Piece(piecename, piecewidth, pieceheight, imagename)
    for p in prototypes:
        piece.set_prototype(p)
    piece.set_back(imagebackname)
    modfile.add_piece(piece)
    modfile.save()
