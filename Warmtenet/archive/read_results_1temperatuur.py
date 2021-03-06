import geopandas as gpd
import pandas as pd
import json
import numpy as np
import matplotlib.pyplot as plt

points = gpd.read_file('/home/rogier/earlybirds/assen_test/AllPoints.shp')
roads = gpd.read_file(r'/home/rogier/earlybirds/assen_test/wegen_wijk.shp')
buildings = gpd.read_file(r'/home/rogier/earlybirds/assen_test/shape/buildings.shp')
#
# points = gpd.read_file(r'C:\Users\Rogier\OneDrive\Warmtenet\All_Points_copy.shp')
# roads = gpd.read_file(r'C:\Users\Rogier\OneDrive\Warmtenet\assen_test\wegen_wijk.shp')
# buildings = gpd.read_file(r'C:\Users\Rogier\OneDrive\Warmtenet\assen_test\shape\buildings.shp')

X = len(points) - 1
H = len(buildings) - 1



idx = points.index.tolist()
source = points.loc[points['osm_id'] == -1].index.values[0]
idx.pop(source)
points = points.reindex(idx+[source])
points.reset_index(drop = True)

PointsInRoads = np.zeros((len(roads.geometry),len(points.geometry)))
PointsInRoadsShort = np.ones((len(roads.geometry),2))*-1

i=0;
j=0;

for road in roads.geometry:
    x = 0;
    for point in points.geometry:
        if road.distance(point) < 1e-8:
            PointsInRoads[i,j] = 1
            PointsInRoadsShort[i,x] = j
            x += 1;
        j += 1
    i += 1
    j = 0



# read file
with open('results_9_1temperatuur_wijk.json', 'r') as myfile:
    data=myfile.read()

# with open('results_10_peakfactor.json', 'r') as myfile:
#     data=myfile.read()

# parse file
obj = json.loads(data)


A = np.zeros([len(points), len(points)], dtype=np.float32)
for i in range(0,len(points)):
    for j in range(0,len(points)):
        try:
            a =  obj['Solution'][1]['Variable']['A['+ str(i) + ',' + str(j) + ']']['Value']
            if a>0.001:
                print ('A [' + str(i) + ',' + str(j) + ']: ', a)
                A[i,j]= a

        except:
            pass

connected=[]
for i in range(0,len(buildings)):
        try:
            a = obj['Solution'][1]['Variable']['Conn['+ str(i) + ']']['Value']
            if a>0.9:
                print('Conn['+ str(i) + ']:', a)
            connected.append(a)
        except:
            connected.append(0)



AreaTube=[]
for row in PointsInRoadsShort:
    AreaTube.append(np.sqrt((A[int(row[0]),int(row[1])] + A[int(row[1]),int(row[0])])/np.pi)*2)
roads['width']=AreaTube
buildings['Conn']=connected

f, ax = plt.subplots()

# roads.iloc[i,:].plot()
#
# df= gpd.GeoDataFrame(data = roads.iloc[i].values, columns = roads.iloc[i].index)

#
# roads.plot(column='width', cmap='hot_r', ax=ax, legend=True)
bins = [0,0.2,0.4,0.7,1,1.5]
colors = ['#FFFE30', '#E8C315', '#E87621', '#FF5531', '#FFB224' ]
roads['binned'] = pd.cut(roads['width'], bins)
rdgroups = roads.groupby('binned')

i=1;
for key, group in rdgroups:
    group.plot(ax=ax, linewidth=4.5*bins[i] +1, color = colors[i-1], label = key )
    i += 1;

plt.legend(title='diameter', loc='upper left')
# for i in range(0, len(roads)):
#
#     roads.iloc[i].to_frame().plot( column='width', ax=ax, linewidth= roads['width'][i])

roads.plot(ax=ax, linewidth=1, color='grey', alpha=0.5)


buildings.plot(column='Conn', vmin=0, vmax=1.5, cmap='Greys', ax=ax, edgecolor='grey')

# for i in range(0, len(roads)):
#

ax.set_axis_off()
plt.show()

