import wx
import wax
import colorsys

from math import pi, cos, sin

class GraphicsCanvas(wx.Frame, wax.waxobject.WaxObject):
    __events__ = {
        'Paint': wx.EVT_PAINT,
    }

    def __init__(self, parent):
        self.Init()


    def _OnPaint(self, event=None):
        self.OnPaint(event)
    def OnPaint(self, event=None):
        dc = wx.PaintDC(self)
        gc = wx.GraphicsContext.Create(dc)
        #self.PrepareDC(dc)
        self.OnDraw(dc)
        event.Skip()

    def OnDraw(self, dc):
        # override to draw on the canvas
        pass

    def Init(self):
        # override to place scrollbars, set color, etc.
        pass


class PieChart(wx.Frame, wax.waxobject.WaxObject):
	def __init__(self, parent, rect, fitrect=None, values=None,
	             relative=None, initial=None):
		""" Create a new PieChart canvas. """
        wx.Frame.__init__(self, parent, wx.NewId())

		# bounding rectangle (and fit-to rectangle)
		self.rect = rect
		self.fit = fitrect

		# set the relative height (must be at least 0.5px)
		self.relative = max(0.5, relative)

		# font used for drawing slice labels
		self.font = wax.Font('Garamond', 12)
		self.fontcolor = 'black'

		# slice edge definition (color will be by contrast value)
		self.edge_size = 2

		# set up the slice values (4-tuple (value, text, displacement, color))
		self.slicevalues = (values is None and ([],) or (values,))[0]
		self.slices = []

		# the initial angle for pie slice placement (inside of 2pi rads)
		self.initialangle = initial % (2 * pi)

		# the currently highlighted rectangle
		self.currenthilite = None

        self.BindEvents()

	def OnDraw(self, dc):
		""" Draw all the slices in the chart, plus strings! """
		if not len(self.slicevalues) or not len(self.slices): return

		# skip repack if it's not needed
		if self.NeedRepack: self.PackSlices(self.fit)

		# draw all the bottom slices
		for slc in self.slices: slc.Draw(dc)

	def DrawText(self, dc):
		""" Draws all the string values for the pie chart. """
		# set the font
		dc.SetFont(self.font, self.fontcolor)

		# draw each slice's string
		for slc in self.slices:
			dc.DrawText(slc.text, slc.textpt[0], slc.textpt[1])

	def GetSliceAt(self, x, y):
		"""
		Get the slice under the selected coordinates (or None).
		Search order goes in the direction opposite to drawing order.
		"""
		# look for slice in pile of slices by calling its contains
		for slc in self.slices:
			if slc.Contains((x, y)):
				return slc

		# see if there's a split on the back slice that we can test for
		#test_back = self.slices[0].Split(1.5 * pi)

		# split the back-most pie slice @ 3pi/2 rad
		#tempslices = self.slices[:]
		#cleave = self.slices[0].Split(1.5 * pi)
		#if len(cleave) > 1:
		#	tempslices[0] = cleave[1]
		#	if cleave[0].sweepangle > 0:
		#		tempslices.append(cleave[0])

		# check peripheries (rounded part of slices)
		# search using partitions
		for i in xrange(len(self.slices) / 2):
			if self.slices[-i+1] == self.slices[i]: break

			# get left and right slices
			lslc = self.slices[-(i+1)]
			rslc = self.slices[i]

			# calculate angles
			langle = (1.5*pi) - lslc.start
			rangle = (rslc.end + (pi/2))
			if rangle > 2*pi: rangle -= 2*pi

			# do increment etc.
			if langle > rangle:
				if rslc.PeripheryContains(x, y): return rslc
			elif lslc.PeripheryContains(x, y): return lslc

		# get the pie slice at the front
		front = 0
		for slc in self.slices:
			if (slc.startangle <= 90 and slc.startangle + slc.sweep >= 90)\
			   or (slc.startangle + slc.sweep > 360 and \
			   (slc.startangle <= 450 and slc.startangle + slc.sweep >= 450)):
					break
			front += 1

		# check for start side containment (starting from the front)
		# look through the slices leading to the back
		for slc in self.slices[i:]:
			if slc.StartSideContains(x, y): return slc

		# look through the slices going towards the back
		for slc in self.slices[:i]:
			if slc.StopSideContains(x, y): return slc

		# check for bottom hit (how would this happen?)
		for slc in self.slices:
			if slc.BottomContains(x, y): return slc

		return None

	def GetFit(self):
		""" Finds the smallest rectangle into which we fit entirely. """
		rectangle = (self.slices[0].rect[0], self.slices[0].rect[1], 0, 0)
		for rect in [slc.rect for slc in self.slices]:
			rectangle[0] = min(rect[0], rectangle[0])
			rectangle[1] = min(rect[1], rectangle[1])
			rectangle[2] = max(rect[2], rectangle[2])
			rectangle[3] = max(rect[3], rectangle[3])
		return rectangle

	def OnSize(self, rect):
		""" Readjusts slices for fitting inside the new rectangle. """
		newx = rect[0] - self.bounds[0]
		newx = rect[1] - self.bounds[1]
		wfactor = self.bounds[2] / rect[2]
		hfactor = self.bounds[3] / rect[3]

		# issue resize call for each slice
		# slc.x -= newx ; slc.y -= newy ; slc.w *= wfactor ; slc.h *= hfactor ; slc.sliceheight *= hfactor
		for slc in self.slices: slc.Resize(newx, newy, wfactor, hfactor)

	def Pack(self):
		"""
		Creates a list of pies, starting with the pie that is crossing the
        270 degrees boundary, i.e. "backmost" pie that always has to be
        drawn first to ensure correct surface overlapping.
        """
		# JK: calculates the sum of values required to sweep angles for slices
		total = sum(self.slicevalues, key=lambda x: x[0])

		# some values and indices that will be used in the loop
		bigdisplace = sum(self.slicevalues, key=lambda x: x[3])
		biggest_ellipse = (self.bounds[2] / (bigdisplace + 1), \
		                   self.bounds[3] / (bigdisplace + 1) * \
		                   (1 - self.relative))
		biggest_displacement = (biggest_ellipse[0] * bigdisplace, \
		                        biggest_ellipse[1] * bigdisplace)
		height = self.bounds[3] / bigdisplace * self.relative

		# set up the angle tracker
		start_angle = self.initial

		# build pie slices from value list
		for info in self.slicevalues:
			# calculate the number of radians this arc will sweep
			sweep = float(info[0]) / total * 2*pi

			# set displacement values
			if info[2] > 0:
				# calculate x/y displacement values
				dx = biggest_ellipse[0] * info[2] / 2 * cos((start_angle + sweep) / 2)
				dy = biggest_ellipse[1] * info[2] / 2 * sin((start_angle + sweep) / 2)
			else: dx, dy = 0, 0

			# bounding box(4-tuple), height, sweep angle, color, edge width
			newslice = PieSlice((dx + self.bounds[0] + biggest_ellipse[0]/2,
			                    dy + self.bounds[1] + biggest_ellipse[1]/2,
			                    biggest_ellipse[0], biggest_ellipse[1]),
			                    height, start_angle, sweep, info[3], self.edge)

			# add text to new slice
			newslice.SetText(info[1])

			# the backmost pie is inserted to the front of the list for correct drawing
			if len(self.slices) > 1 or \
			   (start_angle <= 1.5*pi and start_angle + sweep > 1.5*pi) or \
			   (start_angle >= 1.5*pi and start_angle + sweep > (630/180)*pi):
				self.slices.append(newslice)
			else: self.slices.insert(0, newslice)

			start_angle = start_angle + sweep

	def DrawSliceSides(self, gc):
		""" Draw outer peripheries of all slices (?) """
		# set up tracking variables to see if we should draw the front
		# or back of a slice first (instead of splitting it and doing work)
		draw_first_back_last = False
		draw_first_front_last = False

		# create a temporary slice batch
		#tempslices = copy(self.split)

		# if the first pie slice (in back) is crossing 90 (in front), split
		if self.slices[0].start > (pi/2) and self.slices[0].start <= 1.5*pi and \
		   self.slices[0].start + self.slices[0].sweep > (450/180)*pi:

			# split at 0 rads to hide line from view
			#tempsplit = self.slices[0].Split(0)
			#tempslices[0] = tempsplit[0]
			#if tempsplit[1].sweep > 0: tempslices.append(tempsplit[1])
			draw_first_back_last = True

		# same thing, but on the other side
		elif (self.slices[0].start > 1.5*pi and \
		      self.slices[0].start + self.slices[0].sweep > (450/180)*pi) or \
		     (self.slices[0].start < pi/2 and \
		      self.slices[0].start + self.slices[0].sweep > 1.5*pi):

			# split at pi rads to hide line from view
			#tempsplit = self.slices[0].Split(pi)
			#tempslices[0] = tempsplit[1]
			#if tempsplit[1].sweep > 0: tempslices.append(tempsplit[0])
			draw_first_front_last = True

		# draw the first slice
		if draw_first_back_last:
			self.slices[0].DrawStartSide(gc)
		elif draw_first_front_last:
			self.slices[0].DrawStopSide(gc)
		else:
			self.slices[0].DrawSides(gc)

		# draw the sucessive slices
		for ndx in xrange(1, len(self.slices)/ 2):
			if self.slices[ndx] == self.slices[-ndx]: break

			# set up the left slice and angle
			lslc = self.slices[-ndx]
			langle = lslc.start_angle - (pi/2)
			if langle > pi or langle < 0: langle = 0

			# set up the right slice and angle
			rslc = self.slices[ndx]
			rangle = (450/180*pi) - lslc.start_angle % (2*pi)
			if rangle > pi or rangle < 0: rangle = 0

			# draw based on side angle preference
			if angle2 < angle1:
				lslc.DrawSides(gc) ; rslc.DrawSides(gc)
			else:
				rslc.DrawSides(gc) ; lslc.DrawSides(gc)

		# draw the first slice
		if draw_first_back_last:
			self.slices[0].DrawStopSide(gc)
		elif draw_first_front_last:
			self.slices[0].DrawStartSide(gc)
		else:
			self.slices[-1].DrawSides(gc)

	def DrawBottoms(self, gc):
		""" Draw the bottom of each pie slice """
		for slc in self.slices: slc.DrawBottom(gc)

	def DrawTops(self, gc):
		""" Draw the top of each pie slice """
		for slc in self.slices: slc.DrawTop(gc)


class PieSlice(object):
	"""
	A slice object that lives in a PieChart object.
	FIXME: should subclass a window so that redraw doesn't eat all cpu
	"""
	master_transparency = 90
	hilite_transparency = 120
	edge_transparency = 100

	def __init__(self, rect, height, start, sweep,
	             edge, color='steelblue'):
		# define our bounding box and height
		self.rect = rect
		self.height = height

		# define our angles
		self._start = start_angle
		self._sweep = sweep
		self.start = None
		self.sweep = None
		self._end = (start_angle + sweep)
		if self._end > 2*pi: self._end -= 2*pi

		# define start and end sides
		self.sides = (Quadrilateral(), Quadrilateral())

		# create a color (and an hsv conversion for highlights/edges/etc.)
		cdata = wax.colordb.byname(color)
		self.color = wx.Colour(cdata[0], cdata[1], cdata[2], master_transparency)
		self.hsv = rgb_to_hsv(cdata[0]/255.0, cdata[1]/255.0, cdata[2]/255.0)
		self.brush = wx.Brush(self.color)

		# create hilite color (lighter and more opaque than the main color)
		cdata = hsv_to_rgb(self.hsv[0], self.hsv[1], self.hsv[2]+.05)
		self.hi_brush = wx.Brush(wx.Colour(cdata[0], cdata[1], cdata[2], hilite_transparency))

		# tweak contrast for visibility and create pen (more opaque than main)
		contrast = self.hsv[2] + (self.hsv[2] > 0.4 and (.3,) or (-.3,))[0]
		cdata = hsv_to_rgb(self.hsv[0], self.hsv[1], contrast)
		self.pen = wx.Pen(wx.Colour(cdata[0], cdata[1], cdata[2], edge_transparency), edge)

		# create shadow color (same opacity as the main color)
		self.shade_brush = wx.Brush(wx.Colour(cdata[0], cdata[1], cdata[2], master_transparency))

		# Convenience Functions
		# transform angle to 3d coordinates (and get it back)
		self.Project = lambda r, a: atan2(r[2] * sin(a), r[3] * cos(a))
		self.Unproject = lambda r, a: atan2(r[3] * cos(a), r[2] * sin(a))

		# get a point on the periphery of the arc
		self.Periphery = lambda r, a:(r[0] + (r[2] * cos(a)), r[1] + (r[3] * sin(a)))

		# resize self and pack
		self.Size(rect, height)
		self.Pack()

		# create brush for start side of slice (s_shadowAngle = 20F)
#		shadow_angle = self.start_angle - (pi - pi/18)
#		if shadow_angle < 0: shadow_angle += 2*pi
#		fudge = -(.3 * (1 - 0.8 * cos(angle)))
#		colordata = colorsys.hsv_to_rgb(self.hsv[0], self.hsv[1], self.hsv[2]+fudge)
#		self.start_color = wx.Colour(colordata[0], colordata[1], colordata[2], 90)

		# create brush for end side of slice
#		shadow_angle = self.start_angle + self.sweep - (pi/18)
#		if shadow_angle < 0: shadow_angle += 2*pi
#		fudge = -(.3 * (1 - 0.8 * cos(angle)))
#		colordata = colorsys.hsv_to_rgb(self.hsv[0], self.hsv[1], self.hsv[2]+fudge)
#		self.end_color = wx.Colour(colordata[0], colordata[1], colordata[2], 90)

		# unfortunately, wx DOESN'T HAVE color stops for linear gradients
		# this post has information on how Chandler did it:
		# http://lists.osafoundation.org/pipermail/commits/2005-April/004578.html
		# also, investigate this algorithm:
		# http://incubator.quasimondo.com/processing/superfastblur.pde

		# create brush for cylindrical side
#		precolor = colorsys.hsv_to_rgb(self.hsv[0], self.hsv[1], self.hsv[2]-0.15)
#		postcolor = colorsys.hsv_to_rgb(self.hsv[0], self.hsv[1], self.hsv[2]-0.3)
#		multigrad = ((precolor, 0), (color, 0.1), (postcolor, 1))
#		fillmap = self.MakeMultiLinearGradient(self.rect, multigrad)


	def Pack(self):
		""" Recalculate everything. """
		# define start and sweep angles
		self.start = self.Project(self.rect, self._start)
		self.sweep = ((self._sweep / pi != 0) and \
		             (self.Project(self.rect, self._start + self._sweep) - self._sweep,) or \
		             (self._sweep,))[0]
		if self.sweep < 0: self.sweep + (2 * pi)

		# calculate center and center bounding box
		cx, cy = (self.rect[0] + self.rect[2]/2, self.rect[1] + self.rect[3]/2)
		temprect = (cx, cy, self.rect[2] / 2, self.rect[3] / 2)

		# create center points
		self.center = (cx, cy)
		self.center_below = (cx, cy + self.height)

		# create starting and ending points
		self.startpt = self.Periphery(modrect, self._start)
		self.startpt_below = (self.startpt[0], self.startpt[1] + self.height)
		self.endpt =  self.Periphery(modrect, self._start + self._sweep)
		self.startpt_below = (self.endpt[0], self.endpt[1] + self.height)

		# update quadrilaterals
		self.side[0].Update(self.center, self.startpt, self.center_below,
		                    self.startpt_below, self.sweep != pi)
		self.side[1].Update(self.center, self.endpt, self.center_below,
		                    self.endpt_below, self.sweep != pi)

	def Contains(self, x, y):
		""" Hit detection for mouseover, etc. """
		PieSliceContainsPoint(point)
		PeripheryContainsPoint(point)

		# check the quadrilaterals
		if self.sides[0].Contains(point) or self.sides[1].Contains(point):
			return True

		return False

	def TextPosition(self):
		""" Get the middle of the slice (for text drawing, etc.) """
		# calculate the theoretical middle of the slice
		temprect = (self.center[0], self.center[1], self.rect[2]/3, self.rect[3]/3)

		# if the arc is more than half, get a position in the hemisphere
		if self.sweep >= pi:
			return self.PPt(temprect, Unproject(self.start) + self.sweep / 2)

		# get a point inside the slice
		tempx = ((self.startpt[0] + self.endpt[0]) / 2) - self.center[0]
		tempy = ((self.startpt[1] + self.endpt[1]) / 2) - self.center[1]
		tempangle = atan2(tempy, tempx)

		return self.PPt(temprect, self.Unproject(tempangle))

	def OnDraw(dc):
		""" Draw the slice """
		# convert dc to native and get a graphicscontext
		gc = wx.GCDC(dc)
		gcon = gc.GetGraphicsContext()

		# draw the bottom and back layers first
		self.DrawPieslice(gc, top=0)
		for section in GetHiddenPeriphery():
			DrawCylinderSection(gcon, self.brush, section)

		# draw the sides in order
		if pi/2 < self.start < 1.5*pi:
			self.DrawSide(gc, 0) ; self.DrawSide(gc)
		else: self.DrawSide(gc) ; self.DrawSide(gc, 0)

		# draw the visible cylinders and the top pie slice
		for section in GetVisiblePeriphery():
			DrawCylinderSection(gcon, self.brush, section)
		self.DrawPieslice(gc, top=1)


	def DrawCylinderSurfaceSection(gcon, brush):
		# get a graphics context path
		path = gcon.CreatePath()

		# set up the shading and the pen
		gc.SetPen(self.pen)
		gc.SetBrush(self.shade_brush)

		# draw arcs and lines
		#FIXME: I don't know if this works ... let's wait and see!
		path.AddArc(self.center[0], self.center[1], self.start *(2*pi), (self.end - self.start) * (2*pi))
		path.AddLine(self.endpt[0], self.endpt[1], self.endpt[0], self.endpt[1]+ self.height)
		path.AddArc(self.center[0], self.center[1] + self.height, self.end *(2*pi), (self.start - self.end) * (2*pi))
		path.AddLine(self.startpt[0], self.startpt[1]+ self.height, self.startpt[0], self.startpt[1])


	def DrawSide(gc, startside=1):
		""" Draw the visible start side. """
		# get the selected side to draw
		side = (startside and (self.sides[0],) or (self.sides[1],))[0]
		angle = (startside and (self.start,) or (self.end,))[0]

		# if this side is visible, draw it with the appropriate brush
		brush = ((pi/2 < angle < 1.5*pi) and (self.shade_brush,) or (self.brush,))[0]

		# draw the side with the brush
		side.Draw(gc, self.pen, brush)

	def DrawPieslice(dc, top=1):
		""" Draws the actual EllipticArc. """
		rect = copy(self.rect)
		if not top: rect[1] += self.height

		# draw and fill the arc
		gc.SetBrush(self.brush)
		gc.SetPen(self.pen)
		gc.DrawEllipticArc(rect[0], rect[1], rect[2], rect[3],
		                   self.start * (2*pi), self.end * (2*pi))

	def Split(self, split_angle):
		""" Can we split this slice at the given angle? """
		# we have an edge at the given boundary, so it's fine
		return not (self.start == angle or self.end == angle)

	def PeripheryContains(self, x, y):
		""" Checks if given point is contained by cylinder periphery. """
		surfaces = GetVisiblePeripherySurfaceBounds

		for surface in surfaces:
			if CylinderSurfaceSectionContains(x, y, self.start, self.end):
				return True
		return False

	def BottomSurfaceSectionContains(self, x, y):
		""" Checks if the bottom pie slice contains the given coordinates. """
		if not self.height: return False

		return PieSliceContains(x, y, self.rect, self.start, self.sweep)

	def GetVisiblePeripherySurfaceBounds(self):
		""" Get the boundaries for the visible cylindrical surfaces. """
		bounds = []

		# 
        /// <summary>
        ///   Gets an array of visible periphery bounds.
        /// </summary>
        /// <returns>
        ///   Array of <c>PeripherySurfaceBounds</c> objects.
        /// </returns>
        private PeripherySurfaceBounds[] GetVisiblePeripherySurfaceBounds() {
            ArrayList peripherySurfaceBounds = new ArrayList();
            // outer periphery side is visible only when startAngle or endAngle
            // is between 0 and 180 degrees
            if (!(m_sweepAngle == 0 || (m_startAngle >= 180 && m_startAngle + m_sweepAngle <= 360))) {
                // draws the periphery from start angle to the end angle or left
                // edge, whichever comes first
                if (StartAngle < 180) {
                    float fi1 = m_startAngle;
                    PointF x1 = new PointF(m_pointStart.X, m_pointStart.Y);
                    float fi2 = EndAngle;
                    PointF x2 = new PointF(m_pointEnd.X, m_pointEnd.Y);
                    if (m_startAngle + m_sweepAngle > 180) {
                        fi2 = 180;
                        x2.X = m_boundingRectangle.X;
                        x2.Y = m_center.Y;
                    }
                    peripherySurfaceBounds.Add(new PeripherySurfaceBounds(fi1, fi2, x1, x2));
                }
                // if lateral surface is visible from the right edge
                if (m_startAngle + m_sweepAngle > 360) {
                    float fi1 = 0;
                    PointF x1 = new PointF(m_boundingRectangle.Right, m_center.Y);
                    float fi2 = EndAngle;
                    PointF x2 = new PointF(m_pointEnd.X, m_pointEnd.Y);
                    if (fi2 > 180) {
                        fi2 = 180;
                        x2.X = m_boundingRectangle.Left;
                        x2.Y = m_center.Y;
                    }
                    peripherySurfaceBounds.Add(new PeripherySurfaceBounds(fi1, fi2, x1, x2));
                }
            }
            return (PeripherySurfaceBounds[])peripherySurfaceBounds.ToArray(typeof(PeripherySurfaceBounds));
        }

        /// <summary>
        ///   Gets an array of hidden periphery bounds.
        /// </summary>
        /// <returns>
        ///   Array of <c>PeripherySurfaceBounds</c> objects.
        /// </returns>
        private PeripherySurfaceBounds[] GetHiddenPeripherySurfaceBounds() {
            ArrayList peripherySurfaceBounds = new ArrayList();
            // outer periphery side is not visible when startAngle or endAngle
            // is between 180 and 360 degrees
            if (!(m_sweepAngle == 0 || (m_startAngle >= 0 && m_startAngle + m_sweepAngle <= 180))) {
                // draws the periphery from start angle to the end angle or right
                // edge, whichever comes first
                if (m_startAngle + m_sweepAngle > 180) {
                    float fi1 = m_startAngle;
                    PointF x1 = new PointF(m_pointStart.X, m_pointStart.Y);
                    float fi2 = m_startAngle + m_sweepAngle;
                    PointF x2 = new PointF(m_pointEnd.X, m_pointEnd.Y);
                    if (fi1 < 180) {
                        fi1 = 180;
                        x1.X = m_boundingRectangle.Left;
                        x1.Y = m_center.Y;
                    }
                    if (fi2 > 360) {
                        fi2 = 360;
                        x2.X = m_boundingRectangle.Right;
                        x2.Y = m_center.Y;
                    }
                    peripherySurfaceBounds.Add(new PeripherySurfaceBounds(fi1, fi2, x1, x2));
                    // if pie is crossing 360 & 180 deg. boundary, we have to
                    // invisible peripheries
                    if (m_startAngle < 360 && m_startAngle + m_sweepAngle > 540) {
                        fi1 = 180;
                        x1 = new PointF(m_boundingRectangle.Left, m_center.Y);
                        fi2 = EndAngle;
                        x2 = new PointF(m_pointEnd.X, m_pointEnd.Y);
                        peripherySurfaceBounds.Add(new PeripherySurfaceBounds(fi1, fi2, x1, x2));
                    }
                }
            }
            return (PeripherySurfaceBounds[])peripherySurfaceBounds.ToArray(typeof(PeripherySurfaceBounds));
        }

        /// <summary>
        ///   Creates <c>GraphicsPath</c> for cylinder surface section. This
        ///   path consists of two arcs and two vertical lines.
        /// </summary>
        /// <param name="startAngle">
        ///   Starting angle of the surface.
        /// </param>
        /// <param name="endAngle">
        ///   Ending angle of the surface.
        /// </param>
        /// <param name="pointStart">
        ///   Starting point on the cylinder surface.
        /// </param>
        /// <param name="pointEnd">
        ///   Ending point on the cylinder surface.
        /// </param>
        /// <returns>
        ///   <c>GraphicsPath</c> object representing the cylinder surface.
        /// </returns>
        private GraphicsPath CreatePathForCylinderSurfaceSection(float startAngle, float endAngle, PointF pointStart, PointF pointEnd) {
            GraphicsPath path = new GraphicsPath();
            path.AddArc(m_boundingRectangle, startAngle, endAngle - startAngle);
            path.AddLine(pointEnd.X, pointEnd.Y, pointEnd.X, pointEnd.Y + m_sliceHeight);
            path.AddArc(m_boundingRectangle.X, m_boundingRectangle.Y + m_sliceHeight, m_boundingRectangle.Width, m_boundingRectangle.Height, endAngle, startAngle - endAngle);
            path.AddLine(pointStart.X, pointStart.Y + m_sliceHeight, pointStart.X, pointStart.Y);
            return path;
        }

        /// <summary>
        ///   Checks if given point is contained within upper and lower pie
        ///   slice surfaces or within the outer slice brink.
        /// </summary>
        /// <param name="point">
        ///   <c>PointF</c> structure to check for.
        /// </param>
        /// <param name="startAngle">
        ///   Start angle of the slice.
        /// </param>
        /// <param name="endAngle">
        ///   End angle of the slice.
        /// </param>
        /// <param name="point1">
        ///   Starting point on the periphery.
        /// </param>
        /// <param name="point2">
        ///   Ending point on the periphery.
        /// </param>
        /// <returns>
        ///   <c>true</c> if point given is contained.
        /// </returns>
        private bool CylinderSurfaceSectionContainsPoint(PointF point, float startAngle, float endAngle, PointF point1, PointF point2) {
            if (m_sliceHeight > 0) {
                return Quadrilateral.Contains(point, new PointF[] { point1, new PointF(point1.X, point1.Y + m_sliceHeight), new PointF(point2.X, point2.Y + m_sliceHeight), point2 } );
            }
            return false;
        }

        /// <summary>
        ///   Checks if point given is contained within the pie slice.
        /// </summary>
        /// <param name="point">
        ///   <c>PointF</c> to check for.
        /// </param>
        /// <param name="xBoundingRectangle">
        ///   x-coordinate of the rectangle that bounds the ellipse from which
        ///   slice is cut.
        /// </param>
        /// <param name="yBoundingRectangle">
        ///   y-coordinate of the rectangle that bounds the ellipse from which
        ///   slice is cut.
        /// </param>
        /// <param name="widthBoundingRectangle">
        ///   Width of the rectangle that bounds the ellipse from which
        ///   slice is cut.
        /// </param>
        /// <param name="heightBoundingRectangle">
        ///   Height of the rectangle that bounds the ellipse from which
        ///   slice is cut.
        /// </param>
        /// <param name="startAngle">
        ///   Start angle of the slice.
        /// </param>
        /// <param name="sweepAngle">
        ///   Sweep angle of the slice.
        /// </param>
        /// <returns>
        ///   <c>true</c> if point is contained within the slice.
        /// </returns>
        private bool PieSliceContainsPoint(PointF point, float xBoundingRectangle, float yBoundingRectangle, float widthBoundingRectangle, float heightBoundingRectangle, float startAngle, float sweepAngle) {
            double x = point.X - xBoundingRectangle - widthBoundingRectangle / 2;
            double y = point.Y - yBoundingRectangle - heightBoundingRectangle / 2;
            double angle = Math.Atan2(y, x);
            if (angle < 0)
                angle += (2 * Math.PI);
            double angleDegrees = angle * 180 / Math.PI;
            // point is inside the pie slice only if between start and end angle
            if ((angleDegrees >= startAngle && angleDegrees <= (startAngle + sweepAngle)) ||
                (startAngle + sweepAngle > 360) && ((angleDegrees + 360) <= (startAngle + sweepAngle))) {
                // distance of the point from the ellipse centre
                double r = Math.Sqrt(y * y + x * x);
                return GetEllipseRadius(angle) > r;
            }
            return false;
        }

        /// <summary>
        ///   Evaluates the distance of an ellipse perimeter point for a
        ///   given angle.
        /// </summary>
        /// <param name="angle">
        ///   Angle for which distance has to be evaluated.
        /// </param>
        /// <returns>
        ///   Distance of the point from the ellipse centre.
        /// </returns>
        private double GetEllipseRadius(double angle) {
            double a = m_boundingRectangle.Width / 2;
            double b = m_boundingRectangle.Height / 2;
            double a2 = a * a;
            double b2 = b * b;
            double cosFi = Math.Cos(angle);
            double sinFi = Math.Sin(angle);
            // distance of the ellipse perimeter point
            return (a * b) / Math.Sqrt(b2 * cosFi * cosFi + a2 * sinFi * sinFi);
        }

        /// <summary>
        ///   Internal structure used to store periphery bounds data.
        /// </summary>
        private struct PeripherySurfaceBounds {
            public PeripherySurfaceBounds(float startAngle, float endAngle, PointF startPoint, PointF endPoint) {
                m_startAngle = startAngle;
                m_endAngle = endAngle;
                m_startPoint = startPoint;
                m_endPoint = endPoint;
            }

            public float StartAngle {
                get { return m_startAngle; }
            }

            public float EndAngle {
                get { return m_endAngle; }
            }

            public PointF StartPoint {
                get { return m_startPoint; }
            }

            public PointF EndPoint {
                get { return m_endPoint; }
            }

            private float m_startAngle;
            private float m_endAngle;
            private PointF m_startPoint;
            private PointF m_endPoint;
        }

