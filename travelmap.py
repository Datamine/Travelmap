# John Loeber | Sep 3 2014 | Python 2.7.4 | Debian Linux
# Pygeocoder 1.2.5
# Documentation: http://www.johnloeber.com/docs/travelmap_documentation.html

import pyproj
from PIL import Image, ImageDraw
from sys import argv,exit
from pygeocoder import Geocoder
from time import sleep
from numpy import linspace
from matplotlib.pyplot import cm

def err(n):
    """
    Prints appropriate error message given error code.
    """
    errors = {2:"lines",3:"colors",4:"Image File"}
    print "Erroneous input for the " + errors[n] + " argument. Aborting."
    exit(0)

def start():
    """
    To parse initial arguments, etc.
    """
    if len(argv)!=5:
        print "Incorrect number of arguments supplied. Aborting."
        exit(0)
    if argv[2].lower()=='y':
        lines = True
    elif argv[2].lower()=='n':
        lines = False
    else:
        err(2)
    if argv[3].lower()=='y':
        colors = True
    elif argv[3].lower()=='n':
        colors = False
    else:
        err(3)
    try:
        img = Image.open(argv[4])
    except:
        err(4)
    if (not lines) and colors:
        print "Incongruous input: lines off, colors on. Aborting."
        exit(0)
    f = open(argv[1],"r")
    
    # removes all lines starting with '#' from the input textfile, to allow
    # the user to supply files with comment-lines.
    text = filter(lambda y: y[0]!='#', f.readlines())
    f.close()
    return text,lines,colors,img

def f7(seq):
    """
    Makes a set from a list, while preserving order.
    From http://stackoverflow.com/a/480227
    """
    seen = set()
    seen_add = seen.add
    return [x for x in seq if not (x in seen or seen_add(x))]

def makecoords(f):
    """
    Turns textfile of locations into list of corresponding pixel-coordinates.
    """
    # sets the map projection from which we are converting to WGS84
    mapfrom = pyproj.Proj(init='EPSG:4326')
    # sets the map projection to which we are converting to Robinson
    p = '+proj=robin +lon_0=0 +x_0=0 +y_0=0 +ellps=WGS84 +datum=WGS84 +units=m +no_defs'
    mapto = pyproj.Proj(p)

    # textfile -> list of places
    places = map(lambda x: x.strip('\n'), f)
    
    # remove duplicates from places while preserving order of the list.
    # this is to minimize the number of calls made to the google maps api
    setplaces = f7(places)
    # list of places -> list of corresponding geographic coordinates (WGS84)
    # creation of dictionary etc. is to create a set of coordinates
    # to avoid repeat lookups of coords and repeat drawings of markers
    dcs = {}
    for i in range(len(setplaces)):
        # Printing status messages to indicate progress.
        print "Geocoding " + setplaces[i]   
        c = Geocoder.geocode(setplaces[i]).coordinates
        # transform WGS84 to Robinson. Swapping x/y is necessary for the format.
        finalpair = pyproj.transform(mapfrom,mapto,c[1],c[0])
        dcs[setplaces[i]] = finalpair
        # Google doesn't allow for more than 10 queries per second. This
        # code throttles the number of requests a little bit, so as to
        # comply with usage limits as in:
        # https://developers.google.com/maps/documentation/business/articles/usage_limits
        if i%10==0:
            sleep(2)
    gcoords = []
    for i in places:
        gcoords.append(dcs[i])
    # transform Robinson to Pixel-Coords. Recall: PIL puts (0,0) in top left. 
    # below: robinson projection offset from (0,0) at the center of the map
    robw = 17005833.33052523
    robh = 8625154.471849944
    # following specs are set for the two maps included with this script.
    # image dimensions
    imgw = 2058
    imgh = 1050
    # space surrounding the map in the imagefile: width and height. (offsets)
    w = 8
    h = 7
    # scaling the coordinates according to the dimensions and offsets of the map.
    mapw = imgw - (2*w)
    maph = imgh - (2*h)
    scalew = (robw*2) / mapw
    scaleh = -(robh*2) / maph
    xc = lambda x: (x+robw)/scalew + w
    yc = lambda y: (y-robh)/scaleh + h
    return [(xc(x),yc(y)) for (x,y) in gcoords], \
           [(xc(x),yc(y)) for (x,y) in dcs.values()]

def check(setcoords,lines):
    """
    Sanity-check input parameters.
    """
    if len(setcoords)==0:
        print "No coordinates located: verify your input file. Aborting."
        exit(0)
    elif len(setcoords)==1 and lines:
        print "Error: Lines turned ON, but only one coordinate location."
        exit(0)

def makelines(draw,pxcoords,colorlist,allcolors,colorscheme,lsc,lsw,linestroke,lw):
    """
    Draw lines to connect the markers on the map.
    """
    for k in range(len(pxcoords)-1):
        # fetches the color of this line
        fillcolor = colorlist[allcolors.index(colorscheme[k])]
        if linestroke:
            # draw the stroke
            draw.line([(pxcoords[k][0],pxcoords[k][1]), \
                      (pxcoords[k+1][0],pxcoords[k+1][1])],fill=lsc,width=lsw+lw)
        # draw the actual line
        draw.line([(pxcoords[k][0],pxcoords[k][1]), \
                  (pxcoords[k+1][0],pxcoords[k+1][1])],fill=fillcolor,width=lw)

def makemarkers(draw,setcoords,r,sw,dotcolor,strokecolor,markerstroke):
    """
    Draw markers on the map corresponding to the pixel coordinates.
    """
    for pair in setcoords:
        # first draw one circle, then superimpose another circle to get
        # the 'stroked circle' effect
        if markerstroke:
            quad2 = (pair[0]-(r+sw),pair[1]-(r+sw),pair[0]+r+sw,pair[1]+r+sw)
            draw.ellipse(quad2,fill=strokecolor)
        quad = (pair[0]-r,pair[1]-r,pair[0]+r,pair[1]+r)
        draw.ellipse(quad,fill=dotcolor)

def main():
    ## GRAPHICAL CONFIGURATION :: SET YOUR OPTIONS HERE ## --------------------
    # see for guidance on colors: http://effbot.org/imagingbook/imagecolor.htm
    
    # settings for markers (dots) and their strokes (=outlines).
    # (if you want unstroked circles, just set markerstroke to False.)
    markerstroke = True
    dotcolor = "red" 
    strokecolor = "white"
    # set the radius of the circular marker, and set the width of the stroke.
    r = 5
    sw = 1

    # settings for lines connecting points. if you want unstroked lines, set
    # linestroke to False. set color of line stroke with lsc.
    linestroke = True
    lsc = "white"
    # set the thickness of your line-stroke. (NB: in PIL 1.1.5, the lines are
    # twice as wide as they should be. This will be fixed in PIL 1.1.6)
    lsw = 3
    # set the width of the connecting line itself.
    lw = 2

    # if all lines are to be just one color, set it here.
    linecolor = "orange"    
    # for when you turn 'colors' on, a colormap will be used to determine the
    # colors of the different line-types. 'jet' is one of the default colormaps 
    # included. see matplotlib.org/api/pyplot_summary.html for alternatives.
    cmap = cm.jet
    
    # Other graphical configuration options are at the end of the makecoords
    # function. Set those if you need to use a different map.

    ## END OF GRAPHICAL CONFIGURATION ## --------------------------------------

    # fin: textfile in; colors: use just one color for the makers, 
    # or color each class of connections differently
    # lines: if you want lines to connect the markers
    # wmap: the image of a Robinson Map, which you are projecting points on
    fin,lines,colors,wmap = start()  
    if colors:
        # selecting locations only, skipping over the linecolor specifiers
        f = fin[::2]
    else:
        f = fin
    
    # pxcoords: the pixel-coordinates of every location in the input file
    # setcoords: the set of unique pxcoords. we use 'pxcoords' to draw
    # connecting lines, and we use setcoords to draw markers, to avoid drawing
    # repeats for markers listed multiple times in the input file.
    pxcoords,setcoords = makecoords(f)
    check(setcoords,lines)
    draw = ImageDraw.Draw(wmap)
    
    # configuring the lines
    if lines:
        if colors:  
            # getting the 'color' of each connection between nodes
            cscheme = fin[1::2]
            allcolors = f7(cscheme)
            colors = cmap(linspace(0.1,0.9,len(allcolors)))
            # intermediary step: convert to list of colors, remove the alpha arg
            z = map(lambda x: x[:3], colors.tolist())
            # formatting the list of colors.    
            clist = ["rgb("+str(int(100*x[0]))+"%,"+str(int(100*x[1]))
                           +"%,"+str(int(100*x[2]))+"%)" for x in z]
        else:
            cscheme = [1] * (len(pxcoords)-1)
            allcolors = [1]
            clist = [linecolor]
        makelines(draw,pxcoords,clist,allcolors,cscheme,lsc,lsw,linestroke,lw)
    
    # drawing markers, saving the end result
    makemarkers(draw,setcoords,r,sw,dotcolor,strokecolor,markerstroke)
    wmap.save("Plotted_"+argv[1]+"_"+argv[4],"PNG")
        
if __name__=='__main__':
    main()
