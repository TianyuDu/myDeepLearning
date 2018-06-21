# https://medium.com/@anthony_sarkis/
# tensorboard-quick-start-in-5-minutes-e3ec69f673af

# General Settings.
from meta import *
para = parameter_control()

print("Loading Packages...")
import tensorflow as tf
import numpy as np
import pandas as pd

import matplotlib
if para.on_server:
	matplotlib.use(
		"agg",
		warn=False,
		force=True
		)  # If on a server, change matplotlib settings.
import matplotlib.pyplot as plt
from datetime import datetime
from sklearn import preprocessing

print("Done.")

# Fetch data from Fred.

ts, TS = fetch_local_single("./data/CPIAUCSL.csv")

scaler = preprocessing.StandardScaler().fit(TS)

TS = scaler.transform(TS)

# ts, TS = fetch_fred_single("CPIAUCSL")

num_periods = para.num_periods
f_horizon = para.f_horizon  # Forecasting period.

x_data = TS[:(len(TS) - (len(TS) % num_periods))]
x_batches = x_data.reshape(-1, num_periods, 1)

y_data = TS[1: (len(TS) - (len(TS) % num_periods)) + 1]
y_batches = y_data.reshape(-1, num_periods, 1)

X_test, Y_test = test_data(TS, f_horizon, num_periods)

tf.reset_default_graph()

inputs = 1
hidden = [32, 64]
output = 1

# Input feed node.
X = tf.placeholder(
	tf.float32,
	[None, num_periods, inputs],
	name="input_label_feed_X")

# Output node.
y = tf.placeholder(tf.float32,
	[None, num_periods, output],
	name="output_label_feed_y")

multi_layers = [
	tf.nn.rnn_cell.BasicRNNCell(num_units=hidden[0]),
	tf.nn.rnn_cell.LSTMCell(num_units=hidden[1], cell_clip=100)
	]

multi_cells = tf.nn.rnn_cell.MultiRNNCell(multi_layers)

rnn_output, states = tf.nn.dynamic_rnn(
	multi_cells,
	inputs=X,
	dtype=tf.float32)

learning_rate = 0.001

stacked_rnn_output = tf.reshape(rnn_output, [-1, hidden[-1]], name="stacked_rnn_output")
stacked_outputs = tf.layers.dense(stacked_rnn_output, output, name="stacked_outputs")

outputs = tf.reshape(stacked_outputs, [-1, num_periods, output])

loss, loss_metric = gen_loss_tensor(outputs, y, metric="mse")


optimizer = tf.train.AdamOptimizer(learning_rate=learning_rate)
training_op = optimizer.minimize(loss)

init = tf.global_variables_initializer()

def train():
	with tf.Session() as sess:
		writer = tf.summary.FileWriter("output", sess.graph)
		# tf.summary.histogram("loss", loss)
		# tf.summary.histogram("outputs", outputs)
		init.run()
		print("Tensors initialized.")
		print("Training...")
		begin_time = datetime.now()

		loss_record = [1]
		for ep in range(para.epochs):
			sess.run(training_op, feed_dict={X: x_batches, y: y_batches})
			if ep % 100 == 0:
				quantified_loss = loss.eval(feed_dict={X: x_batches, y: y_batches})
				loss_record.append(quantified_loss)
				print(ep, f"\t{loss_metric}:", quantified_loss)
				print(f"\tLoss change (Negative -> Improvement): {(loss_record[-1] - loss_record[-2]) / loss_record[-2] * 100} %.")
				# print(f"\t\tLoss improvement {(loss_record[-1] - loss_record[-2]) / loss_record[-2]} %.")
		y_pred = sess.run(outputs, feed_dict={X: X_test})
		print(y_pred)
		writer.close()

		print("Finished, time taken {} seconds".format())

	y_pred = scaler.inverse_transform(y_pred)
	y_data = scaler.inverse_transform(y_data)

	pred = [None] * len(np.ravel(y_data))
	pred[-len(np.ravel(y_pred)):] = np.ravel(y_pred)

	plt.plot(pd.Series(np.ravel(y_data)), alpha=0.6, linewidth=0.5)
	plt.plot(pd.Series(pred), alpha=0.8, linewidth=0.5)

	if not on_server:
		plt.show()

	now_str = datetime.strftime(datetime.now(), "%Y_%m_%d_%s")
	plt.savefig(f"./figure/result{now_str}_all.svg", format="svg")



if __name__ == "__main__":
	train()






