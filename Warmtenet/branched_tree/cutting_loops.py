import geopandas as gpd
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pandas.io.json import json_normalize
import json
import io
from utils import split_line_with_points


crs = {'init': 'epsg:28992'}


# points_with_house_and_source = gpd.read_file('../data/loops_district/Aansluitpunten.geojson')
# points_with_house = points_with_house_and_source[points_with_house_and_source['pandidentificatie'] != 'BRON']
# points_with_house.loc[:, 'pandidentificatie'] = [str(p[1:]) for p in points_with_house['pandidentificatie']]
# index_bron = points_with_house_and_source[points_with_house_and_source['pandidentificatie'] == 'BRON'].index.values[0]
#
# junctions = gpd.read_file('../data/loops_district/Kruispunten.geojson')
# points = pd.concat([points_with_house_and_source, junctions], ignore_index=True, sort=False)
roads = gpd.read_file('../data/loops_district/Wegen.geojson')
#
# # points_unique_geometry.geometry = [geom.centroid for geom in points_unique_geometry.geometry]
#
# #see what point are so near to one another that they should be treated as one
# point_same = {}
# unique_points = []
# for index, point in points.iterrows():
#     point_list = []
#     if index not in unique_points:
#         for index2, point2 in points.iterrows():
#             if point.geometry.distance(point2.geometry) < 1e-1 and index != index2:
#                 point_list.append(index2)
#                 if index2 not in unique_points:
#                    unique_points.append(index2)
#     point_same[index] = point_list
#
# # get all panden together on that single point
# panden={}
# to_remove = []
# for key in point_same.keys():
#     if point_same[key]:
#        andere_panden = [i for i in points.loc[point_same[key], 'pandidentificatie'].values if i is not None]
#        eigen_pand = points.loc[key,  'pandidentificatie']
#        if eigen_pand is not None:
#            andere_panden.append(eigen_pand)
#        panden[key] = str(andere_panden)
#        to_remove.extend(point_same[key])
#     else:
#        panden[key] = "[]"
#
# alle_panden = pd.Series(panden, name='alle_panden')
# points_unique_geometry = pd.concat([points, alle_panden], axis=1)
# points_unique_geometry = points_unique_geometry.drop(to_remove).reset_index()

points_unique_geometry = gpd.read_file('./point_unique_geometry.geojson')

        # see what roads contain multiple points (roads that do not go only from one to another point)
long_roads = {}
road_point_count = np.zeros(roads.shape[0], dtype=int)

for i, road in enumerate(roads.geometry):
    x = 0
    p_array = []
    for j, point in enumerate(points_unique_geometry.geometry):
        if road.distance(point) < 1e-1:
            x += 1
            p_array.append(j)
    if x > 2:
        long_roads[i] = p_array
    road_point_count[i] = x

# split roads that contain multiple points in smaller parts
smaller_parts = []
for road_number, segments in long_roads.items():
    points_in_long_road = []
    distance = []
    for j in segments:
        distance.append(roads.geometry[road_number].project(points_unique_geometry.geometry[j]))
        points_in_long_road.append(points_unique_geometry.geometry[j])

    df_points_in_road = pd.DataFrame({'dis': distance})
    points_gpd = gpd.GeoDataFrame(df_points_in_road , crs=crs, geometry=points_in_long_road)
    points_gpd.sort_values('dis', inplace=True)
    points_gpd.reset_index(drop=True, inplace=True)
    smaller_parts.extend(split_line_with_points(roads.geometry[road_number], points_gpd.geometry[1:-1]))

# merge split roads with other roads
roads.drop(axis=0, index=long_roads.keys(), inplace=True)
gdf_long_roads_split = gpd.GeoDataFrame(crs=crs, geometry=smaller_parts)
gdf_small_roads = gpd.GeoDataFrame(crs=crs, geometry=roads.geometry)
roads = pd.concat([gdf_small_roads, gdf_long_roads_split], axis=0, ignore_index=True, sort=False)


points_in_road = np.zeros((len(roads.geometry),len(points_unique_geometry.geometry)), dtype=np.int16)
points_in_road_short = np.ones((len(roads.geometry),2),dtype=np.int16)*-1

for i, road in enumerate(roads.geometry):
    x = 0
    for j, point in enumerate(points_unique_geometry.geometry):
        if road.distance(point) < 1e-1:
            points_in_road[i, j] = 1
            points_in_road_short[i, x] = j
            x += 1

# see what points can connect to other points
p2p = {}
cost_streets = {}

for i in range(len(points_in_road_short)):
    if np.logical_and(points_in_road_short[i, 0] != -1, points_in_road_short[i, 1] != -1):
        if points_in_road_short[i, 0] not in p2p.keys():
            p2p[points_in_road_short[i, 0]] = [points_in_road_short[i, 1]]
            cost_streets[points_in_road_short[i, 0]] = [roads.geometry[i].length * 100]
        else:
            p2p[points_in_road_short[i, 0]].append(points_in_road_short[i, 1])
            cost_streets[points_in_road_short[i, 0]].append(roads.geometry[i].length * 100)

        if points_in_road_short[i, 1] not in p2p.keys():
            p2p[points_in_road_short[i, 1]] = [points_in_road_short[i, 0]]
            cost_streets[points_in_road_short[i, 1]] = [roads.geometry[i].length * 100]
        else:
            p2p[points_in_road_short[i, 1]].append(points_in_road_short[i, 0])
            cost_streets[points_in_road_short[i, 1]].append(roads.geometry[i].length * 100)

# cut_loops
print(p2p)

index_bron =  points_unique_geometry[points_unique_geometry['pandidentificatie'] == 'BRON'].index.values[0]

#find loops
loops={}
x=0
loops[x] = [index_bron]
real_loops = []
active_keys = [x]
finished_keys = []
finished_points = []
while len(active_keys) > 0:
    for key in active_keys:
        p_conn = np.array(p2p[loops[key][-1]])
        if len(p_conn) == 1 and loops[key][-1] != index_bron:
            finished_points.extend(loops[key])
            active_keys.remove(key)
            finished_keys.append(key)

        else:
            if len(p_conn) == 1:
                loops[key].append(p_conn[0])
            else:
                for i, p_index in enumerate(p_conn[p_conn!=loops[key][-2]]):
                    if i == 0:
                        if (p_index not in loops[key]) and (finished_points.count(p_index) < 20):
                            loops[key].append(p_index)
                        else:
                            if finished_points.count(p_index) < 20:
                                print('more than 20 times')
                            if p_index in loops[key]:
                                finished_points.extend(loops[key][loops[key].index(p_index):])
                                real_loops.append(loops[key][loops[key].index(p_index):] + [p_index])
                            loops[key].append(p_index)
                            active_keys.remove(key)
                            finished_keys.append(key)
                    if i>0:
                        x += 1
                        loop_orig = loops[key][:-1]
                        loops[x] = loop_orig + [p_index]
                        if (p_index not in loop_orig) and (finished_points.count(p_index) < 20):
                            active_keys.append(x)
                        else:
                            if finished_points.count(p_index) < 20:
                                print('more than 20 times')
                            finished_keys.append(x)
                            if p_index in loop_orig:
                                finished_points.extend(loop_orig[loop_orig.index(p_index):])
                                real_loops.append(loop_orig[loop_orig.index(p_index):] + [p_index])

unique_loops = set(tuple(i) for i in real_loops)

f, ax = plt.subplots()
for loop in unique_loops:
    points_unique_geometry.loc[list(loop)].plot(ax=ax)
roads.plot(ax=ax)
plt.show()

print(len(unique_loops))



