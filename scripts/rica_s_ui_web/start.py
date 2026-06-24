from flask import Flask
from flask import render_template, request
import docker
import os
import datetime

import orch

app = Flask(__name__)
cli = docker.DockerClient(base_url='tcp://172.20.0.1:667')


@app.route('/')
def hello():

	containers = cli.containers.list()

	cont = containers[0]

	# print([c.name for c in containers])

	stages = [
		["Stage 1: Sequencing", [c.name for c in containers if "sq_" in c.name]],
		["Stage 2: Basecalling", [c.name for c in containers if "bc_" in c.name]],
		["Stage 3: Identifying", [c.name for c in containers if "id_" in c.name]],
		["Stage 4: Profiling", [c.name for c in containers if "pr_" in c.name]],
		["Stage 5: Reporting", [c.name for c in containers if "rp_" in c.name]]
	]

	return render_template('start.html', stages=stages)





@app.route('/submitted', methods=["POST"])
def submitted():
	run_id = str(datetime.datetime.now()).replace(
		" ", "_").replace(":", "_").replace("-", "_")
	print("run_id: ", run_id)
	run_params = request.form

	orch.processRun(run_id, run_params)

	return render_template('submitted.html', run_id=run_id)





@app.route('/<string:date>.<string:time>')
def report(date, time):
	id= date+"."+time
	with open("../../output/runs/"+id+"/report.html", 'r', encoding='utf-8') as f: 
		report = f.read()

	run_params = {
		"id": id,
		"report": report
	}
	return render_template('report.html', run_params=run_params)
