#!/usr/bin/env python
import numpy as np
import pickle
import rospy
import rospkg
import os

from sensor_stick.pcl_helper import *
from sensor_stick.training_helper import spawn_model
from sensor_stick.training_helper import delete_model
from sensor_stick.training_helper import initial_setup
from sensor_stick.training_helper import capture_sample
from sensor_stick.features import compute_color_histograms
from sensor_stick.features import compute_normal_histograms
from sensor_stick.srv import GetNormals
from geometry_msgs.msg import Pose
from sensor_msgs.msg import PointCloud2

def get_normals(cloud):
    get_normals_prox = rospy.ServiceProxy('/feature_extractor/get_normals', GetNormals)
    return get_normals_prox(cloud).cluster

class Collector(object):
    def __init__(self):
        rospy.init_node('collector')

        rospack = rospkg.RosPack()
        pkg_root = rospack.get_path('pr2_robot')
        default_path = os.path.join(pkg_root, 'config', 'training_set.sav') 

        self._models = rospy.get_param('~object_list', default=[])
        self._models = [m['name'] for m in self._models]

        self._path = rospy.get_param('~path', default=default_path)
        self._as_feature = rospy.get_param('~as_feature', default=False)
        self._steps = rospy.get_param('~steps', default=16) # steps per model
        self._max_try = rospy.get_param('~max_try', default=8)

    def run(self):
        initial_setup()
        data = {}
        for model_name in self._models:
            model_data = []
            spawn_model(model_name)

            for i in range(self._steps):
                # get_cloud()
                sample_cloud = None
                for j in range(self._max_try):
                    sample_cloud = capture_sample()
                    sample_cloud_arr = ros_to_pcl(sample_cloud).to_array()
                    if sample_cloud_arr.shape[0] == 0:
                        print('Invalid cloud detected')
                    else:
                        break
                # save_data()
                if sample_cloud is not None:
                    if self._as_feature:
                        # Extract histogram features
                        chists = compute_color_histograms(sample_cloud, using_hsv=True)
                        normals = get_normals(sample_cloud)
                        nhists = compute_normal_histograms(normals)
                        feature = np.concatenate((chists, nhists))
                        model_data.append(feature)
                    else:
                        model_data.append(sample_cloud)

            data[model_name] = model_data
            delete_model()

        # save data with pickle
        with open(self._path, 'wb') as f:
            pickle.dump(data, f)

def main():
    collector = Collector()
    collector.run()

if __name__ == "__main__":
    main()
