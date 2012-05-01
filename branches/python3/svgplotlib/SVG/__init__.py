#!/usr/bin/python
# -*- coding: utf-8 -*-
# This is code is commercial software.
# Copyright © 2011 by Runar Tenfjord, Tenko.
import sys
from functools import partial

try:
    from xml.etree import cElementTree as etree
except ImportError:
    from xml.etree import  ElementTree as etree

from svgplotlib.TEX.Parser import Parser
from svgplotlib.TEX.Backends import SVGBackend
from svgplotlib.TEX.Font import BakomaFonts
from svgplotlib.SVG.Viewer import show

# TEX parser and fonts
tex_parser = Parser()
tex_fonts = BakomaFonts()

# Mangle names
MangleDict = lambda d: dict((name.replace('_','-'),value) for name,value in list(d.items()))

def CloneElement(elem):
    '''
    Clone root element and ensure attribs are valid text items
    '''
    attrib = {}
    for name,value in list(elem.attrib.items()):
        if isinstance(value, (tuple,list)):
            attrib[name] = str(value)[1:-1]
        elif name == 'root':
            continue
        else:
            attrib[name] = str(value)
    
    ret = etree.Element(elem.tag, attrib)
    ret.text = elem.text
    ret.tail = elem.tail
    
    for child in elem.getchildren():
        ret.append(CloneElement(child))
        
    return ret

class SVGBase(object):
    '''
    Wrapper class for etree.Element
    as in Python 2.6 and earlier etree.Element
    is a factor function and not a class.
    '''
    def __init__(self, name, **kwargs):
        self.element = element = etree.Element(name, **kwargs)

        for i in dir(element):
            setattr(self,i, getattr(element,i) )

    @property
    def tag(self):
       return self.element.tag

    @property
    def text(self):
       return self.element.text

    @property
    def tail(self):
       return self.element.tail

    @property
    def attrib(self):
       return self.element.attrib
   
class SVGElement(SVGBase):
    '''
    Base class for SVG elements
    '''
    def __init__(self, name, **kwargs):
        # mangle names
        attrib = MangleDict(kwargs)
        
        parent = attrib.pop('parent')
        super(SVGElement,self).__init__(name, **attrib)
        #SVGBase.__init__(self, name, **attrib)
        parent.append(self.element)

class Defs(SVGBase):
    def __init__(self, **kwargs):
        # mangle names
        attrib = MangleDict(kwargs)
        
        parent = attrib.pop('parent')
        super(Defs,self).__init__('defs', **attrib)
        #SVGBase.__init__(self, 'defs', **attrib)
        parent.append(self.element)
        
        root            = attrib.get('root')
        self.Group      = partial(Group,                  parent=self, root = root)
        self.Line       = partial(SVGElement, 'line',     parent=self, root = root)
        self.Polyline   = partial(SVGElement, 'polyline', parent=self, root = root)
        self.Polygon    = partial(SVGElement, 'polygon',  parent=self, root = root)
        self.Rect       = partial(SVGElement, 'rect',     parent=self, root = root)
        self.Circle     = partial(SVGElement, 'circle',   parent=self, root = root)
        self.Ellipse    = partial(SVGElement, 'ellipse',  parent=self, root = root)
        self.Path       = partial(SVGElement, 'path',     parent=self, root = root)
        self.Text       = partial(SVGElement, 'text',     parent=self, root = root)
        
        self.linearGradient = partial(linearGradient, parent=self, root = root)
        self.radialGradient = partial(radialGradient, parent=self, root = root)
    
class TEX(SVGBase):
    def __init__(self, text, **kwargs):
        root = kwargs.pop('root')
        
        self.Use = partial(SVGElement, 'use', parent=self, root = root)
        self.Rect = partial(SVGElement, 'rect', parent=self, root = root)
        
        # mangle names
        attrib = MangleDict(kwargs)
        
        parent = attrib.pop('parent')
        
        x = attrib.pop('x', 0.)
        y = attrib.pop('y', 0.)
        rotation = attrib.pop('rotation', 0.)
        scale = attrib.pop('scale', 1.)
        
        transform = ["translate(%g,%g)" % (x,y)]
        if rotation != 0.:
            transform.append("rotate(%1.1g)" % rotation)
        if scale != 1.:
            transform.append("scale(%g)" % scale)
        
        super(TEX, self).__init__('g',transform=' '.join(transform), **attrib)
        #SVGBase.__init__(self, 'g', transform = " ".join(transform), **attrib)
        parent.append(self.element)
        
        renderer = SVGBackend(self, root)
        box = tex_parser.parse(text, tex_fonts, 24, 72)
        renderer.render(box)
        
class EText(SVGBase):
    '''
    Text with glyps embedded in root object
    'defs' section.
    '''
    def __init__(self, font, text, **kwargs):
        root = kwargs.pop('root')
        
        # mangle names
        attrib = MangleDict(kwargs)
        
        parent = attrib.pop('parent')
        
        x = attrib.pop('x', 0.)
        y = attrib.pop('y', 0.)
        rotation = attrib.pop('rotation', 0.)
        scale = attrib.pop('scale', 1.)
        
        transform = ["translate(%g,%g)" % (x,y)]
        if rotation != 0.:
            transform.append("rotate(%1.1g)" % rotation)
        if scale != 1.:
            transform.append("scale(%g)" % scale)
        
        super(EText, self).__init__('g',transform=' '.join(transform), **attrib)
        #SVGBase.__init__(self, 'g', transform = " ".join(transform), **attrib)
        parent.append(self.element)
        
        # create glyps
        xpositions, glyph_ids, glyps = font.SVGGlyphs(text, root.glyphs)
        for x, glyph_id in zip(xpositions, glyph_ids):
            obj = SVGElement('use', x = "%g" % x, parent = self)
            obj.set('xlink:href', '#%s' % glyph_id)
            self.append(obj.element)
        
        # add to new glyps defs section
        defs = root.defs
        for name, path in glyps.items():
            defs.Path(id = name, d = path)

class Gradient(SVGBase):
    def __init__(self, **kwargs):
        # mangle names
        attrib = MangleDict(kwargs)
        
        parent = attrib.pop('parent')
        super(Gradient,self).__init__( self.__class__.__name__, **attrib )
        #SVGBase.__init__(self, self.__class__.__name__, **attrib)
        parent.append(self.element)
        
        root = attrib.get('root')
        self.Stop = partial(SVGElement, 'stop', parent=self, root = root)
        

class linearGradient(Gradient):
    pass

class radialGradient(Gradient):
    pass
        
class Group(SVGBase):
    def __init__(self, **kwargs):
        # mangle names
        attrib = MangleDict(kwargs)
        
        parent = attrib.pop('parent')
        super(Group, self).__init__('g', **attrib)
        #SVGBase.__init__(self, 'g', **attrib)
        parent.append(self.element)
        
        root = attrib.get('root')
        self.Group    = partial(Group,                  parent=self, root = root)
        self.Use      = partial(SVGElement, 'use',      parent=self, root = root)
        self.Line     = partial(SVGElement, 'line',     parent=self, root = root)
        self.Polyline = partial(SVGElement, 'polyline', parent=self, root = root)
        self.Polygon  = partial(SVGElement, 'polygon',  parent=self, root = root)
        self.Rect     = partial(SVGElement, 'rect',     parent=self, root = root)
        self.Circle   = partial(SVGElement, 'circle',   parent=self, root = root)
        self.Ellipse  = partial(SVGElement, 'ellipse',  parent=self, root = root)
        self.Path     = partial(SVGElement, 'path',     parent=self, root = root)
        self.Text     = partial(SVGElement, 'text',     parent=self, root = root)
        self.EText    = partial(EText,                  parent=self, root = root)
        self.TEX      = partial(TEX,                    parent=self, root = root)
        
class SVG(SVGBase):
    '''
    SVG root element
    
    Due to the SVG use of dashes in attribute names the char '_' is
    mangled to '-' automatic.
    
    SVG element constructors:
    - Defs
    - Use
    - Group
    - Line
    - Polyline
    - Polygon
    - Rect
    - Circle
    - Ellipse
    - Path
    - Text
    - EText (Embedded text)
    - TEX (math formula)
    
    All constructors create a new element with the root object as parent.
    To change the parent of the object pass the 'parent' attribute to the
    constructor.
    
    All constructors except for EText and TEX are standard SVG elements.
    
    Example::
        svg = SVG(width=50, height=50)
        g = svg.Group(stroke = "black")
        svg.Line(x1 = 0, y1 = 0., x2 = 50., y2 = 50., stroke='red', parent = g)
        g.Line(x1 = 0, y1 = 50., x2 = 50., y2 = 0.)
        svg.write('test.svg')
    '''
    HEADER = \
"""<?xml version="1.0" standalone="no"?>
<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" 
  "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">"""
  
    def __init__(self, **kwargs):
        attr = {
            'version' : '1.1',
            'xmlns' : 'http://www.w3.org/2000/svg',
            'xmlns:svg' : 'http://www.w3.org/2000/svg',
            'xmlns:xlink' : 'http://www.w3.org/1999/xlink'
        }
        
        # mangle names
        attrib = MangleDict(kwargs)
        attr.update(attrib)
        
        super(SVG, self).__init__('svg', **attr)
        #SVGBase.__init__(self, 'svg', **attr)
        
        self.Defs       = partial(Defs,                     parent=self, root = self)
        self.Use        = partial(SVGElement, 'use',        parent=self, root = self)
        self.Group      = partial(Group,                    parent=self, root = self)
        self.Line       = partial(SVGElement, 'line',       parent=self, root = self)
        self.Polyline   = partial(SVGElement, 'polyline',   parent=self, root = self)
        self.Polygon    = partial(SVGElement, 'polygon',    parent=self, root = self)
        self.Rect       = partial(SVGElement, 'rect',       parent=self, root = self)
        self.Circle     = partial(SVGElement, 'circle',     parent=self, root = self)
        self.Ellipse    = partial(SVGElement, 'ellipse',    parent=self, root = self)
        self.Path       = partial(SVGElement, 'path',       parent=self, root = self)
        self.Text       = partial(SVGElement, 'text',       parent=self, root = self)
        self.EText      = partial(EText,                    parent=self, root = self)
        self.TEX        = partial(TEX,                      parent=self, root = self)
        
        # embedded font
        self.glyphs = set()
        self.defs = self.Defs()
        
    def write(self, file = sys.stdout, header = True, encoding='utf-8', **kwargs):
        '''
        Writes the element tree to a file, as XML. Attributes
        are converted to valid strings.
        
        file - A file name, or a file object opened for writing.
        header - Write svg decleration header to file
        encoding - Output encoding, default is 'utf-8'
        '''
        if header:
            if encoding is None:
                file.write(SVG.HEADER)
            else:
                file.write(SVG.HEADER.encode(encoding))
            
        tree = etree.ElementTree(CloneElement(self))
        tree.write(file, encoding = encoding, **kwargs)
    
    @property
    def width(self):
        return int(self.get('width', 500))
    
    @property
    def height(self):
        return int(self.get('height', 500))

def show(svg, width = 500, height = 500):
    '''
    Function to show SVG file with Qt
    '''
    import io
    import math
    
    from PyQt4 import QtCore, QtGui, QtSvg
    
    class SvgWidget(QtSvg.QSvgWidget):
        def __init__(self, parent):
            super(SvgWidget, self).__init__(parent)
            self.setFixedSize(width, height)
            
            # white background
            palette = QtGui.QPalette(self.palette()) 
            palette.setColor(QtGui.QPalette.Window, QtGui.QColor('white')) 
            self.setPalette(palette) 
            self.setAutoFillBackground(True) 
            
        def sizeHint(self):
            return QtCore.QSize(width,height)
        
    class MainWindow(QtGui.QMainWindow):
        def __init__(self):
            super(MainWindow, self).__init__()
            self.setMinimumSize(width + 50, height + 50)
            self.setWindowTitle('show')
            
            self.Actions = {
                'Save' : QtGui.QAction(
                    "Save", self, shortcut="Ctrl+S",
                    triggered=self.SaveFile
                ),
                'Quit' : QtGui.QAction(
                    "Quit", self, shortcut="Ctrl+Q",
                    triggered=QtGui.qApp.closeAllWindows
                ),
            }
            
            fileMenu = self.menuBar().addMenu("File")
            fileMenu.addAction(self.Actions['Save'])
            fileMenu.addSeparator()
            fileMenu.addAction(self.Actions['Quit'])
        
            self.svg = SvgWidget(self)
            self.setCentralWidget(self.svg)
            
            fh = io.BytesIO()
            svg.write(fh)
            self.svg.load(QtCore.QByteArray(fh.getvalue()))
        
        def SaveFile(self): 
            dlg = QtGui.QFileDialog.getSaveFileName
            filename = dlg(self, "Save", '', "svg file ( *.svg ) ;; image file ( *.png )")
            
            if filename:
                filename = str(filename)
                
                if filename.endswith('.svg'):
                    fh = open(filename, 'wb')
                    svg.write(fh)
                    fh.close()
                else:
                    fh = io.BytesIO()
                    svg.write(fh)
                    content = QtCore.QByteArray(fh.getvalue())
                    
                    image = QtGui.QImage(width, height, QtGui.QImage.Format_ARGB32_Premultiplied)
                    
                    painter = QtGui.QPainter(image)
                    painter.setViewport(0, 0, width, height)
                    painter.eraseRect(0, 0, width, height)
                    render = QtSvg.QSvgRenderer(content)
                    render.render(painter)
                    painter.end()
                    
                    image.save(filename)
                
            
            
    app = QtGui.QApplication(sys.argv)
    mw = MainWindow()
    mw.show()
    app.exec_()
    
if __name__ == '__main__':
    import math
    
    svg = SVG(width="150", height="150")
    '''
    g = svg.Group(stroke = "black", transform="translate(75,75)")
    delta = 30
    for angle in range(0,360 + delta,delta):
        x = 70.*math.sin(math.radians(angle))
        y = 70.*math.cos(math.radians(angle))
        g.Line(x1 = 0, y1 = 0, x2 = x, y2 = y)
    '''
    
    svg.TEX('$\sum_{i=0}^\infty x_i$')
    
    #grad = svg.defs.linearGradient(id="MyGradient")
    #grad.Stop(offset="5%", stop_color="#F60")
    #grad.Stop(offset="95%", stop_color="#FF6")
    
    svg.Rect(fill="url(#MyGradient)", stroke="black", stroke_width=5,
             x=0, y=0, width=150, height=150)
    svg.write()
    
    show(svg)
    
