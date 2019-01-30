from hbp_nrp_virtual_coach.virtual_coach import VirtualCoach
import pandas
import csv
import tempfile
import time
import os
import logging

# disable global logging from the virtual coach
logging.disable(logging.INFO)
logging.getLogger('rospy').propagate = False
logging.getLogger('rosout').propagate = False

# log into the virtual coach, update with your credentials
try:
    vc = VirtualCoach(environment='local', storage_username='nrpuser', storage_password='password')
except ImportError as e:
    print(e)
    print("You have to start this notebook with the command:\
          cle-virtual-coach throw_coach.py")
    raise e

brain_template = '''
# -*- coding: utf-8 -*-
"""
Tutorial brain for the throwing experiment
"""

# pragma: no cover
__author__ = 'Jacques Kaiser'

from hbp_nrp_cle.brainsim import simulator as sim
import numpy as np

n_sensors = 3
n_motors = 13

sensors = sim.Population(n_sensors, cellclass=sim.IF_curr_exp())
motors = sim.Population(n_motors, cellclass=sim.IF_curr_exp())
sim.Projection(sensors, motors, sim.AllToAllConnector(),
               sim.StaticSynapse(weight={syn_weight}))

circuit = sensors + motors

'''

record_cylinder_tf = \
'''
# Imported Python Transfer Function
import numpy as np
import sensor_msgs.msg

@nrp.MapCSVRecorder("cylinder_recorder", filename="cylinder_position.csv",
                    headers=["Time", "px", "py", "pz"])
@nrp.Robot2Neuron()
def record_ball_csv(t, cylinder_recorder):
    from rospy import ServiceProxy
    from gazebo_msgs.srv import GetModelState

    model_name = 'cylinder'
    state_proxy = ServiceProxy('/gazebo/get_model_state',
                                    GetModelState, persistent=False)
    cylinder_state = state_proxy(model_name, "world")

    if cylinder_state.success:
        current_position = cylinder_state.pose.position
        cylinder_recorder.record_entry(t,
                                   current_position.x, 
                                   current_position.y, 
                                   current_position.z)
'''

# this name has to match the name passed in the CSV transfer function
csv_name = 'cylinder_position.csv'

def save_position_csv(sim, datadir):
    with open(os.path.join(datadir, csv_name), 'wb') as f:
        cf = csv.writer(f)
        csv_data = sim.get_csv_data(csv_name)
        cf.writerows(csv_data)


# The function make_on_status() returns a on_status() function
# This is called a "closure":
# it is here used to pass the sim and datadir objects to on_status()
def make_on_status(sim, datadir):
    def on_status(msg):
        print("Current simulation time: {}".format(msg['simulationTime']))
        if msg['simulationTime'] == 5.0 and sim.get_state() == 'started':
            sim.pause()
            save_position_csv(sim, datadir)
            sim.stop()
            print("Trial terminated - saved CSV in {}".format(datadir))

    return on_status


def run_experiment(datadir, brain_params={'syn_weight': 1.0}):
    #################################################
    # Insert code here:
    # 1) launch the experiment
    # 2) add the status callback
    # 3) add the parametrized brain file
    # 4) add the extra CSV TF
    # 5) start the simulation
    #################################################
    brain_file = brain_template.format(**brain_params)

    sim = vc.launch_experiment('template_manipulation_0')
    sim.register_status_callback(make_on_status(sim, datadir))
    sim.add_transfer_function(record_cylinder_tf)
    sim.edit_brain(brain_file) #solution
    sim.start()
    return sim


tmp_folder = tempfile.mkdtemp()
print('start expe !!!')
sim = run_experiment(datadir=tmp_folder)

# wait for sim to be finished
while sim.get_state() != 'stopped':
    time.sleep(3)

csv_file = os.path.join(tmp_folder, csv_name)
print("Recorded the following csv file: {}".format(csv_file))

cylinder_csv = pandas.read_csv(csv_file)
print(cylinder_csv)