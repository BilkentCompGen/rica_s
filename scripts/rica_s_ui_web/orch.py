import os
import docker

def processRun(run_id, run_params):

	cli = docker.DockerClient(base_url='tcp://172.20.0.1:667')
	containers = cli.containers.list()

	cont = containers[0]
	# setup config
	# check directories

	os.mkdir("/rica_s/output/runs/"+run_id)
	os.mkdir("/rica_s/output/runs/"+run_id+"/sq")
	os.mkdir("/rica_s/output/runs/"+run_id+"/bc")
	os.mkdir("/rica_s/output/runs/"+run_id+"/id")
	os.mkdir("/rica_s/output/runs/"+run_id+"/pr")
	os.mkdir("/rica_s/output/runs/"+run_id+"/rp")



	sq_containers = [c.name for c in containers if "sq_" in c.name]
	bc_containers = [c.name for c in containers if "bc_" in c.name]
	id_containers = [c.name for c in containers if "id_" in c.name]
	pr_containers = [c.name for c in containers if "pr_" in c.name]
	rp_containers = [c.name for c in containers if "rp_" in c.name]
	
	# sq

	# bc
	
	# id
	for id_cont in id_containers:
		cont = cli.containers.get(id_cont)#! /bin/bash
		print("[i] running "+id_cont)
		
		
		cmd = "/rica_s/tools/"+id_cont+"/identify_reads.sh "+run_id+" "+run_params["tb_readpath"]
		print("[i] command: "+cmd)
		
		(exit_code, output)=cont.exec_run(f"sh -c '{cmd}'", privileged=True)
		print("[i] "+id_cont+" ended")
		print("[i] exit_code: "+str(exit_code))
		print("[i] output: "+str(output))
	# pr
	
	# rp 
	
	
	
	return 