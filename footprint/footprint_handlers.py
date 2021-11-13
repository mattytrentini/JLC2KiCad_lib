import json
import logging 
from math import pow

from KicadModTree import *
from footprint.model3d import *

layer_correspondance = {
	"1" : "F.Cu", 
	"2" : "B.Cu", 
	"3" : "F.SilkS", 
	"4" : "B.Silks",  
	"5" : "F.Paste", 
	"6" : "B.Paste",  
	"7" : "F.Mask",  
	"8" : "B.Mask",
	"12" : "F.Fab",
	"100" : "F.SilkS",
	"101" : "F.SilkS",
	}

def mil2mm(data):
	return(float(data)/3.937)

def h_TRACK(data, kicad_mod, footprint_info):

	data[0] = mil2mm(data[0])

	width = data[0]
	points = [mil2mm(p) for p in data[2].split(" ")]
	
	for i in range(int(len(points)/2) - 1 ): 

		start = [points[2*i], points[2*i + 1]]     
		end   = [points[2*i + 2], points[2*i + 3]]
		try :
			layer = layer_correspondance[data[1]]
		except :
			logging.exception("footprint h_TRACK: layer correspondance not found")
			layer = "F.SilkS"

		#update footprint borders 
		footprint_info.max_X = max(footprint_info.max_X, start[0], end[0]) 
		footprint_info.min_X = min(footprint_info.min_X, start[0], end[0]) 
		footprint_info.max_Y = max(footprint_info.max_Y, start[1], end[1]) 
		footprint_info.min_Y = min(footprint_info.min_Y, start[1], end[1]) 

		#append line to kicad_mod 
		kicad_mod.append(Line(start=start, 
							end=end,
							width= width,  
							layer= layer))	
	
def h_PAD(data, kicad_mod, footprint_info):
	shape_correspondance = {
		"OVAL" : "SHAPE_OVAL",
		"RECT" : "SHAPE_RECT",
		"ELLIPSE" : "SHAPE_CIRCLE",
		"POLYGON" : "SHAPE_CUSTOM",
	}
	
	rotation = 0
	primitives = ""

	if footprint_info.assembly_process == "SMT" :

		data[1] = mil2mm(data[1])
		data[2] = mil2mm(data[2])
		data[3] = mil2mm(data[3])
		data[4] = mil2mm(data[4])
		
		pad_type = Pad.TYPE_SMT
		pad_layer = Pad.LAYERS_SMT
		pad_number = data[6]
		if data[0] in shape_correspondance:
			shape = shape_correspondance[data[0]]
		else : 
			logging.error("footprint pad : no correspondance found, using defualt SHAPE_OVAL ")
			shape = "SHAPE_OVAL"

		at = [data[1], data[2]]
		size = [data[3], data[4]]
		
		#update footprint borders 
		footprint_info.max_X = max(footprint_info.max_X, at[0], at[0]) 
		footprint_info.min_X = min(footprint_info.min_X, at[0], at[0]) 
		footprint_info.max_Y = max(footprint_info.max_Y, at[1], at[1]) 
		footprint_info.min_Y = min(footprint_info.min_Y, at[1], at[1]) 
		
		
		if shape == "SHAPE_OVAL":
			rotation = float(data[9])
		elif shape == "SHAPE_CUSTOM":
			points = []
			for i, coord in enumerate(data[8].split(" ")):
				points.append(mil2mm(coord) - at[i%2])
			primitives = [Polygon(nodes=zip(points[::2], points[1::2]))]
		elif shape == "SHAPE_CIRCLE":
			pass
		elif shape == "SHAPE_RECT":
			rotation  = float(data[9])
		
		drill = 1

	elif footprint_info.assembly_process == "THT":
		data[1] = mil2mm(data[1])
		data[2] = mil2mm(data[2])
		data[3] = mil2mm(data[3])
		data[4] = mil2mm(data[4])
		data[7] = mil2mm(data[7])

		pad_type = Pad.TYPE_THT
		pad_layer = Pad.LAYERS_THT
		pad_number = data[6]
		shape = shape_correspondance[data[0]]
		at = [data[1], data[2]]
		size = [data[3], data[4]]
		rotation = 0 #TODO 
		drill = data[7] * 2

	else :
		logging.warning("unknown assembly_process: " + footprint_info.assembly_process)
		return()

	# update footprint borders 
	footprint_info.max_X = max(footprint_info.max_X, data[1]) 
	footprint_info.min_X = min(footprint_info.min_X, data[1]) 
	footprint_info.max_Y = max(footprint_info.max_Y, data[2]) 
	footprint_info.min_Y = min(footprint_info.min_Y, data[2]) 
	

	kicad_mod.append(Pad(number = pad_number, 
						 type = pad_type, 
						 shape = getattr(Pad, shape),
						 at = at, 
						 size = size, 
						 rotation = rotation,
						 drill = drill,
						 layers = pad_layer,
						 primitives = primitives))

def h_ARC(data, kicad_mod, footprint_info):
	#append an Arc to the footprint
	try :
		# parse the data  
		if data[2][0] == "M":
			startX, startY, midX, midY, _, _, _, endX, endY = [val for val in data[2].replace("M", "").replace("A", "").replace(",", " ").split(" ") if val]
		elif data[3][0] == "M":
			startX, startY, midX, midY, _, _, _, endX, endY = [val for val in data[3].replace("M", "").replace("A", "").replace(",", " ").split(" ") if val]
		else :
			logging.warning("failed to parse footprint ARC data")
		width = data[0]

		width = mil2mm(width)
		startX = mil2mm(startX)
		startY = mil2mm(startY)
		midX = mil2mm(midX)
		midY = mil2mm(midY)
		endX = mil2mm(endX)
		endY = mil2mm(endY)

		start = [startX, startY]
		end = [endX, endY]
		midpoint = [end[0] + midX, end[1] + midY]
		
		sq1 = pow(midpoint[0],2) + pow(midpoint[1],2) - pow(start[0], 2) - pow(start[1], 2)
		sq2 = pow(end[0],2) + pow(end[1],2) - pow(start[0], 2) - pow(start[1], 2)

		centerX = ((start[1]-end[1])/(start[1]-midpoint[1])*sq1 - sq2) / (2*(start[0]-end[0])-2*(start[0]-midpoint[0])*(start[1]-end[1])/(start[1]-midpoint[1]))
		centerY = -(2*(start[0]-midpoint[0])*centerX+sq1)/(2*(start[1]-midpoint[1]))
		center = [centerX, centerY]
		
		try :
			layer = layer_correspondance[data[1]]
		except KeyError :
			logging.warning('footprint Arc : layer correspondance not found')
			layer = "F.SilkS"

		kicad_mod.append(Arc(center=center, 
							start = start, 
							end = end, 
							width = width, 
							layer=layer))
	except :
		logging.exception("footprint : failed to add ARC")

def h_CIRCLE(data, kicad_mod, footprint_info):
	#append a Circle to the footprint

	if data[4] == "100" : # they want to draw a circle on pads, we don't want that. This is an empirical deduction, no idea if this is correct, but it seems to work on my tests 
		return()

	data[0] = mil2mm(data[0])
	data[1] = mil2mm(data[1])
	data[2] = mil2mm(data[2])
	data[3] = mil2mm(data[3])

	center = [data[0], data[1]]
	radius = data[2]
	width = data[3]

	try :
		layer = layer_correspondance[data[4]]
	except KeyError :
		logging.exception('Schematic Circle : footprint layer correspondance not found')
		layer = "F.SilkS"

	kicad_mod.append(Circle(center= center, 
							radius= radius, 
							width = width, 
							layer = layer))

def h_SOLIDREGION(data, kicad_mod, footprint_info):
	pass

def h_SVGNODE(data, kicad_mod, footprint_info):
	#create 3D model as a WRL file
	
	get_3Dmodel(component_uuid = json.loads(data[0])["attrs"]["uuid"],
				footprint_info = footprint_info, 
				kicad_mod = kicad_mod,
				translationZ = json.loads(data[0])["attrs"]["z"],
				rotation = json.loads(data[0])["attrs"]["c_rotation"])

def h_VIA(data, kicad_mod, footprint_info):
	logging.warning("VIA not supported. Via are often added for better heat dissipation. Be careful and read datasheet if needed.")

handlers = {
	"TRACK" : h_TRACK, 
	"PAD" : h_PAD, 
	"ARC" : h_ARC, 
	"CIRCLE" : h_CIRCLE, 
	"SOLIDREGION" : h_SOLIDREGION, 
	"SVGNODE" : h_SVGNODE, 
	"VIA" : h_VIA,
}