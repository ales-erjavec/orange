#
# Module: Orange Dendrograms
# --------------------------
#
# CVS Status: $Id$
#
# Author: Aleks Jakulin (jakulin@acm.org)
#
# Purpose: Dendrogram rendering for hierarchical clustering.
#
# Project initiated on 2003/05/09
#
# Notes: 
#   Classes GDHClustering and GHClustering are subclasses of the orngCluster's
#   DHClustering and HClustering, but they have an additional method dendrogram()
#   which outputs a piddle canvas with the image of the dendrogram.
#
# ChangeLog:
#   2003/05/13:
#       - line_size
#   2003/07/18:
#       - support for other canvases 
#   2003/09/12:
#       - cluster identification
#   2003/09/18:
#       - coloring, line width
#       - dissimilarity matrix visualization
#   2004/02/16:
#       - latent variable visualization
#       - black&white dissimilarity matrix


import orngCluster
import Tkinter, ImageTk
import piddle, piddlePIL, math


def _colorize0(cc):
    #bluefunc = lambda cc:1.0 / (1.0 + math.exp(-10*(cc-0.6)))
    #redfunc = lambda cc:1.0 / (1.0 + math.exp(10*(cc-0.5)))    
    bluefunc = lambda cc:1.0 / (1.0 + math.exp(-10*(cc-0.6)))
    redfunc = lambda cc:1.0 / (1.0 + math.exp(10*(cc-0.5)))
    cblu = bluefunc(cc)
    cred = redfunc(cc)
    cgre =  1 - pow(redfunc(cc+0.1),2) - bluefunc(cc-0.15)
    #cgre =  1 - pow(redfunc(cc+0.2),2) - bluefunc(cc-0.3)
    return piddle.Color(cred,cgre,cblu)

def _colorize1(cc):
    bluefunc = lambda cc:1.0 / (1.0 + math.exp(-10*(cc-0.6)))
    redfunc = lambda cc:1.0 / (1.0 + math.exp(10*(cc-0.5)))
    cred = bluefunc(cc)
    cgre = redfunc(cc)
    cblu =  1 - pow(redfunc(cc+0.1),2) - bluefunc(cc-0.15)
    return piddle.Color(cred,cgre,cblu)

def _blackwhite(cc):
    v = 1.0-(1.0/cc)
    return piddle.Color(v,v,v)

class DendrogramPlot:    
    def dendrogram(self,labels,width = 500, height = None, margin = 20, hook = 40, line_size = 2.0, cluster_colors = [], canvas = None, line_width = 1,color_mode=0, incremental_height=1, matr = [], g_lines=0):
        # prevent divide-by-zero...
        if len(labels) < 2:
            return canvas

        ## ADJUST DIMENSIONS ###        

        if canvas == None:
            tcanvas = piddlePIL.PILCanvas()
        else:
            tcanvas = canvas

        if height==None:
            # compute the height
            lineskip = int(line_size*tcanvas.fontHeight()+1)
            height = int(2.0*margin + lineskip*(len(labels)-1) + tcanvas.fontHeight()+1)
        else:
            # compute lineskip
            lineskip = (height - 2.0*margin - tcanvas.fontHeight()) / (len(labels)-1)
        maxlabel = 0.0
        for s in labels:
            maxlabel = max(maxlabel,tcanvas.stringWidth(s))

        if canvas == None:
            canvas = piddlePIL.PILCanvas(size=(width,height))

        if len(matr)>0:
            block = lineskip/2-1
        else:
            block = 0

        if color_mode:
            _colorize = _colorize1 # gregor
        else:
            _colorize = _colorize0 # aleks


        ### EXTRACT THE DENDROGRAM ###
        
        vlines = []               # vertical lines (cluster)
        hlines = []               # horizontal lines (clusters)
        origins = [0.0]*self.n    # text positions
        xpositions = [0.0]*self.n # cluster x positions (height)
        ypositions = [0]*self.n   # cluster y positions (average element)
        attcolors = [0]*self.n
        y = margin
        for i in range(len(labels)):
            # self.order identifies the label at a particular row
            ypositions[self.n-self.order[i]] = y
            y += lineskip
        xpositions.append("sentry")
        ypositions.append("sentry")
        p = self.n
        # bottom-up construction
        height = 0.0
        displacement = 0.0
        for i in range(self.n-1):
            if len(cluster_colors) == self.n-1:
                coloV = _colorize(cluster_colors[i][0])
                coloH = _colorize(cluster_colors[i][1])
            else:
                # no color information
                coloH = coloV = piddle.black
            # obtain the height
            if incremental_height:
                nheight = min(xpositions[p+self.merging[i][0]],xpositions[p+self.merging[i][1]])
                nheight -= self.height[i]
                displacement = min(displacement,nheight)
            else:
                height -= self.height[i]
                nheight = height

            vlines.append((nheight,ypositions[p+self.merging[i][0]],ypositions[p+self.merging[i][1]],coloV))
            avg = 0.0
            for j in self.merging[i]:
                # record text origins
                v = ypositions[p+j]
                if j < 0:
                    origins[-1-j] = nheight
                    attcolors[-1-j] = coloH
                else:
                    # create the cluster lines
                    hlines.append((v,xpositions[p+j],nheight,coloH))
                avg += v             
            # recompute the average height of new cluster
            ypositions.append(0.5*avg)
            xpositions.append(nheight)            
        #print displacement
        ### DRAWING ###            
                
        offset = width-maxlabel-hook-2*margin
        if len(matr)>0:
            offset -= 2*(len(matr[0])+1)*block # correct the right-hand side
        hs = (offset-margin)/(height-displacement)         # height scaling
        if incremental_height:
            hs = -hs
        halfline = canvas.fontAscent()/2.0

        # print line-guides
        if g_lines and len(matr)==len(labels):
            colo = piddle.Color(0.9,0.9,0.9)
            y = margin
            s = len(matr[0])
            sx1 = width-margin-block            
            sx2 = width-margin-2*(len(matr[0]))*block-block
            canvas.drawLine(sx1,y-block-1,sx2,y-block-1,colo,width=0.2)
            for i in range(len(labels)):
                idx = self.order[i]-1
                x1 = offset+hook-hs*(origins[idx])+tcanvas.stringWidth(labels[idx])+4
                x2 = width-margin-block
                canvas.drawLine(x1,y,x2,y,colo,width=0.2)
                canvas.drawLine(x1,y,x2,y,colo,width=0.2)
                canvas.drawLine(sx1,y+block+1,sx2,y+block+1,colo,width=0.2)
                y += lineskip
            for i in range(len(matr[0])+1):
                x = width-margin-2*i*block-block
                canvas.drawLine(x,margin-block,x,y-lineskip+block+1,colo,width=0.2)

        # print names
        y = margin
        for i in range(len(labels)):
            # self.order identifies the label at a particular row
            idx = self.order[i]-1
            x = offset-hs*(origins[idx])
            canvas.drawString(labels[idx], hook+x, y+halfline)
            # draw the hook
            canvas.drawLine(x,y,x+hook*0.8,y,attcolors[idx],width=line_width)
            y += lineskip

        # print lines
        for (y,x1,x2,colo) in hlines:
            canvas.drawLine(offset-(x1)*hs,y,offset-(x2)*hs,y,colo,width=line_width)
        vlines.reverse() # smaller clusters are more interesting
        for (x,y1,y2,colo) in vlines:
            canvas.drawLine(offset-(x)*hs,y1,offset-(x)*hs,y2,colo,width=line_width)

        ### MATRIX RENDERING ###
        if len(matr)==len(labels):
            y = margin
            for i in range(len(labels)):
#                print labels[i],matr[i]
                idx = self.order[i]-1
                mm = matr[idx]
                for j in range(len(mm)):
                    # self.order identifies the label at a particular row
                    x = width-margin-2*(len(mm)-j)*block
                    v = 1-mm[j]
                    #if v < 254.0/255.0:
                    colo = piddle.Color(v,v,v)
                    canvas.drawRect(x-block+1,y-block,x+block-1,y+block,edgeColor=colo,fillColor=colo)
                y += lineskip
            
        canvas.flush()
        return canvas

    def matrix(self,labels, diss, margin = 10, hook = 10, block = None, line_size = 2.0, att_colors = [], canvas = None,color_mode=0):
        # prevent divide-by-zero...
        if len(labels) < 2:
            return canvas

        ## ADJUST DIMENSIONS ###        

        if canvas == None:
            tcanvas = piddlePIL.PILCanvas()
        else:
            tcanvas = canvas

        # compute the height
        lineskip = int(line_size*tcanvas.fontHeight()+1)
        labellen = [tcanvas.stringWidth(s) for s in labels]
        maxlabel = max(labellen)
        width = height = int(1 + 2.0*margin + hook + maxlabel + max(lineskip*(0.5+len(labels)) + tcanvas.fontHeight(),2*maxlabel))

        if block == None:
            block = lineskip/2-1

        if canvas == None:
            canvas = piddlePIL.PILCanvas(size=(width,height))


        if color_mode==1:
            _colorize = _colorize1 # gregor
        elif color_mode==0:
            _colorize = _colorize0 # aleks
        else:
            _colorize = _blackwhite

        ### DRAWING ###
                
        offset = maxlabel+margin
        halfline = canvas.fontAscent()/2.0

        # print names
        for i in range(len(labels)):
            # self.order identifies the label at a particular row
            idx = self.order[i]-1
            x = offset - labellen[idx] + lineskip/2
            y = offset + lineskip*(i+1)
            canvas.drawString(labels[idx], x, y+block)
            x = offset + lineskip/2
            y = offset + lineskip*(i+1)
            canvas.drawString(labels[idx], y+block, x, angle=90)
            for j in range(i):
                idx2 = self.order[j]-1
                colo = _colorize(diss[max(idx,idx2)-1][min(idx,idx2)])
                x = offset+hook+lineskip*(i+1)
                y = offset+hook+lineskip*(j+1)
                canvas.drawRect(x-block,y-block,x+block,y+block,edgeColor=colo,fillColor=colo)
                canvas.drawRect(y-block,x-block,y+block,x+block,edgeColor=colo,fillColor=colo)
            if len(att_colors) > 0:
                # render the gain
                x = offset+hook+lineskip*(i+1)
                colo = _colorize(att_colors[idx])
                canvas.drawRect(x-block,x-block,x+block,x+block,edgeColor=colo,fillColor=colo)
                
        canvas.flush()
        return canvas

class GDHClustering(DendrogramPlot,orngCluster.DHClustering):
    pass

class GHClustering(DendrogramPlot,orngCluster.HClustering):
    pass


class ViewImage:
    class PicCanvas:
        def draw(self):
            self.canvas = Tkinter.Canvas(self.master,width=self.pic.width(),height=self.pic.height())
            self.canvas.pack()
            self.canvas.create_image(0,0,anchor=Tkinter.NW,image=self.pic)
        
        def __init__(self,master,pic):
            self.master = master
            self.pic = pic
            self.draw()

    def __init__(self,pic):
        self.root = Tkinter.Tk()
        self.root.title("ViewImage")
        self.canvas = self.PicCanvas(self.root,ImageTk.PhotoImage(pic))
        self.root.mainloop()

class ViewCanvas:
    def __init__(self,canvas):
        self.root = Tkinter.Tk()
        self.root.title("ViewCanvas")
        self.canvas = canvas
        self.root.mainloop()

if __name__== "__main__":
    import orange, orngInteract
    import warnings
    warnings.filterwarnings("ignore",module="orngInteract")

    tab = orange.ExampleTable('zoo.tab')
    im = orngInteract.InteractionMatrix(tab)
    (diss,labels) = im.exportDissimilarityMatrix()
    c = GDHClustering(diss)
    canvas = c.dendrogram(labels)
    canvas.getImage().save("c_zoo.png")
    ViewImage(canvas.getImage())

    (dissx,labels,gains) = im.exportDissimilarityMatrix(show_gains = 0, color_coding = 1, color_gains = 1)
    canvas = c.matrix(labels,dissx,att_colors = gains)
    canvas.getImage().save("m_zoo.png")
    ViewImage(canvas.getImage())