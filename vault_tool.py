import requests
import glob
import argparse
import os
import sys
import json
import yaml
import hvac 
import re

from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

main_config_file = "vars/default.yaml"

client = ""
client_src = ""
client_dst = ""

mount_point = ""
mount_point_src = ""
mount_point_dst = ""


secrets = {}
secret_file = ""

sync_file = ""

jobs = ""

final_structure = {}

def client(args,inventory=None,method=None,source=None,target=None):
	global client
	global client_src
	global client_dst

	global mount_point
	global mount_point_src
	global mount_point_dst

	global final_structure

	global secrets
	global secret_file
	global sync_file

	global jobs
	if inventory != None:
		file_check(inventory)
	clusters = list(final_structure.get("vault_cfg",{}).get("clusters",{}).keys())
	secrets = final_structure.get("vault_cfg",{}).get("secrets") 
	for sec in secrets:
		file_check(sec)	
		with open(sec) as f:
			data = yaml.safe_load(f) or {}
			secrets = merge(secrets,data)
	if method == None:
		if args.src not in clusters:
			print(f"{args.src} not in inventory")
			exit(1)
		url = final_structure.get("vault_cfg",{}).get("clusters",{}).get(args.src,{}).get("url")
		token = final_structure.get("vault_cfg",{}).get("clusters",{}).get(args.src,{}).get("token")
		if  not url or not token:
			print("No Token / Url Provided")
			sys.exit(1)	
		client = hvac.Client(url=url, token=token,verify=False)
		if args.src == "master": 
			response = client.sys.list_mounted_secrets_engines()['data']
			mount_point = (sorted(response.keys()))
		else:
			mount_point = [args.src]
	else:
		token_client = final_structure.get("vault_cfg",{}).get("clusters",{}).get(source,{}).get("token") 
		token_target = final_structure.get("vault_cfg",{}).get("clusters",{}).get(target,{}).get("token") 
		url_client = final_structure.get("vault_cfg",{}).get("clusters",{}).get(source,{}).get("url") 
		url_target = final_structure.get("vault_cfg",{}).get("clusters",{}).get(target,{}).get("url") 
		if  not url_client or not token_client or not token_target or not url_target:
			print("No Token / Url Provided")
			sys.exit(1)	
		client_src = hvac.Client(url=url_client, token=token_client,verify=False)
		client_dst = hvac.Client(url=url_target, token=token_target,verify=False)

		# No anymore differences between master and normal cluster
		try:
			response_src = client_src.sys.list_mounted_secrets_engines()['data']
			mount_point_src = (sorted(response_src.keys()))
		except hvac.exceptions.Forbidden:
			print(f"Permission denied while getting secrets engines for {source} ")
			mount_point_src = [source]

		try:
			response_dst = client_dst.sys.list_mounted_secrets_engines()['data']
			mount_point_dst = (sorted(response_dst.keys()))
		except hvac.exceptions.Forbidden:
			print(f"Permission denied while getting secrets engines for {target} ")
			mount_point_dst = [target]

		
def list_all_recursive(client,path='',mount_point=''):
	secrets_found = []
	try:
		response = client.secrets.kv.v2.list_secrets(path=path, mount_point=mount_point)
		keys = response['data']['keys']
	except hvac.exceptions.InvalidPath:
		return []


	for key in keys:
		if key.endswith('/'):
			sub_path = f"{path}{key}" if path else key
			secrets_found.extend(list_all_recursive(client,sub_path, mount_point))
		else:
			full_path = f"/{mount_point}/{path}{key}" if path else f"/{mount_point}/{key}" 
			secrets_found.append(full_path)
	return secrets_found

def list_keys(args):
	global client
	global mount_point
	secrets = []
	if not getattr(args,'cluster',None):
		for mp in mount_point:
			all_secrets = list_all_recursive(client,mount_point=mp.replace('/',''))
			secrets += all_secrets
	else:
		if args.cluster in [s.replace('/','') for s in mount_point]:
			if args.src != 'master':
				all_secrets = list_all_recursive(client,mount_point="master")
			else:
				all_secrets = list_all_recursive(client,mount_point=args.cluster)
			secrets += all_secrets
		else:
			print("Cluster not found")
			sys.exit(1)
	return secrets

def list_secrets(secrets):	
	secret_list = []
	for sec in secrets:
		mount_point_tmp,path=sec.strip('/').split("/",1)
		response = client.secrets.kv.v2.read_secret_version(path=path,mount_point=mount_point_tmp,raise_on_deleted_version=True)
		secret_list.append({"key":sec,"data":response['data']['data']})
	return secret_list


def merge(base, new):
	if isinstance(base, dict) and isinstance(new, dict):
		for k, v in new.items():
			base[k] = merge(base.get(k), v)
		return base
	if isinstance(base, list) and isinstance(new, list):
		return base + new
	return new

def file_check(file):
	if os.path.isfile(file) == False:
		print(f"File: {file} does not exist")
		sys.exit(1)

def make_structure(secrets,dir=None,src=None):
	for entry in secrets:
		base_directory = entry["key"]
		split = base_directory.split('/')
		if len(split) >=  4:	
			mount_point = split[1] 
			namespace = split[2]
			secret_name = split[3]
			new_path = f"/{mount_point}/ns/{namespace}/secret/{secret_name}"
			for filename,content in entry["data"].items():
				if dir != None:
					full_path = os.path.join(f"{dir}{src}{new_path}",filename)
					os.makedirs(f"{dir}{src}{new_path}",exist_ok=True)
					with open(full_path, "w") as f:
						f.write(content)
					print(os.path.abspath(full_path))
				else:
					print(new_path)

def handle_list(args):
	client(args)
	secrets_keys = list_keys(args)
	secrets = list_secrets(secrets_keys)
	if not args.dir and not args.inline:
		json_string = '\n'.join(json.dumps(item) for item in secrets)
		print(json_string)
	else:
		make_structure(secrets)	

def handle_backup(args):
	client(args)
	secrets_keys = list_keys(args)
	secrets = list_secrets(secrets_keys)
	if os.path.isdir(args.dir) == False:
		print("Dir doesn't exists, please create it")
		sys.exit(1)
	make_structure(secrets,args.dir,args.src)

def handle_restore(args):
	print(args.src)

def handle_sync(args):
	global final_structure
	actions = list(final_structure.get("vault_cfg").get("actions").keys())
	import_files = check_type_files('sync',actions)
	for file in import_files:
		path_list = []
		if os.path.isfile(file) == False:
			print("File does not exists")
			exit(1)
		with open(file) as f:
			parsed_yaml_file = yaml.safe_load(f)
		if parsed_yaml_file['kind'] == 'sync' and args.src == parsed_yaml_file['target'].split('/')[0]:
			cluster_name = parsed_yaml_file['target'].split('/',1)[1] if len(parsed_yaml_file['target'].split('/',1)) > 1 else args.src 
			for job in parsed_yaml_file["jobs"]:
				client(args,method="sync",source=parsed_yaml_file["source"],target=parsed_yaml_file["target"])
				process_sync_job(job,client_src,client_dst)

def parse_vault_path(full_path):
    clean_path = full_path.lstrip('/')
    parts = clean_path.split('/', 1)
    if len(parts) < 2:
        return parts[0], "" 
    return parts[0], parts[1]

def process_sync_job(job,client_src,client_dst):
	raw_sources = job['source_path']
	sources = raw_sources if isinstance(raw_sources, list) else [raw_sources]
	full_dest = job['destination_path']
	dst_mnt, dst_path_base = parse_vault_path(full_dest)
	for full_src in sources:
		src_mnt, src_path = parse_vault_path(full_src)
		is_directory = full_src.endswith('/')
		if is_directory:
			sync_recursive_folder(client_src,client_dst,src_mnt,src_path,dst_mnt,dst_path_base)
		else:
			final_dst_path = dst_path_base
			if full_dest.endswith('/'):
				filename = src_path.split('/')[-1]
				final_dst_path = os.path.join(dst_path_base, filename)
			sync_single_secret(client_src,client_dst,src_mnt,src_path,dst_mnt,final_dst_path)

def sync_recursive_folder(client_src, client_dst,src_mnt, src_base, dst_mnt, dst_base):
	try:
		list_resp = client_src.secrets.kv.v2.list_secrets(mount_point=src_mnt, path=src_base)
		keys = list_resp['data']['keys']
		for key in keys:
			curr_src = f"{src_base}{key}"
			curr_dst = f"{dst_base}{key}"
			if key.endswith('/'):
				sync_recursive_folder(client_src, client_dst,src_mnt, curr_src, dst_mnt, curr_dst)
			else:
				sync_single_secret(client_src,client_dst, src_mnt, curr_src, dst_mnt, curr_dst)
	except hvac.exceptions.InvalidPath:
		print(f"Error: The path {src_base} does not exist or is incorrect.")

def sync_single_secret(client_src, client_dst, src_mnt, src_path, dst_mnt, dst_path):
	try:
		response = client_src.secrets.kv.v2.read_secret_version(mount_point=src_mnt, path=src_path,raise_on_deleted_version=True)
		data = response['data']['data']
		client_dst.secrets.kv.v2.create_or_update_secret(mount_point=dst_mnt, path=dst_path, secret=data)
		print(f"Ok: {src_mnt}/{src_path} -> {dst_mnt}/{dst_path}")
	except hvac.exceptions.InvalidPath:
		print(f"Skipped: {src_mnt}/{src_path} non found")
	except Exception as e:
		print(f"Error on {src_path}: {e}")



def check_type_files(type,actions):
	import_files = []
	for act in actions:
		tasks  = final_structure.get("vault_cfg").get("actions").get(act) 
		for task in tasks:
			if task["type"] == type:
				if os.path.isfile(task["conf"]):
					if task["conf"] not in import_files:
						import_files.append(task["conf"])
	return import_files

def handle_import(args):
	global final_structure
	global mount_point

	client(args)	
	pattern = r'/ns/([^/]+)/(?:secret|tls-secret)/([^ ]+)/([^ ]+)'
	secrets_data = [] 
	cluster_name = ""
	grouped_secrets = {} 

	# Get all files and check if type import exists
	actions = list(final_structure.get("vault_cfg").get("actions").keys())
	import_files = check_type_files('import',actions)

	# Check if target match
	for file in import_files:
		path_list = []
		if os.path.isfile(file) == False:
			print("File does not exists")
			exit(1)
		with open(file) as f:
			parsed_yaml_file = yaml.safe_load(f)
		if parsed_yaml_file['kind'] == 'import' and args.src == parsed_yaml_file['target'].split('/')[0]:
			cluster_name = parsed_yaml_file['target'].split('/',1)[1] if len(parsed_yaml_file['target'].split('/',1)) > 1 else args.src 
			for cert in parsed_yaml_file["secrets"]["paths"]:
				clean_path = cert.rstrip("*")
				search_pattern = os.path.join(clean_path, "**/*")
				found_items = glob.glob(search_pattern, recursive=True)
				for item in found_items:
					if not os.path.isdir(item):
						if item not in path_list:
							path_list.append(item)
				for path in path_list:
					match = re.search(pattern,path)
					ns = match.group(1)
					secret_name = match.group(2)
					secret_key = match.group(3)
					value = {"ns": ns,"secret_name": secret_name,"secret_key": secret_key,"secret_data_file": path,"cluster": cluster_name}
					if value not in secrets_data:
						secrets_data.append(value)
#       Import certs	
	
	for item in secrets_data:
		vault_path = f"{item['ns']}/{item['secret_name']}"
		cluster = item['cluster'] #Check default with thomas
		try:
			with open(item['secret_data_file'],'r') as f:
				secret_value = f.read().strip()
		except Exception as e: 
			print(f"Error in the file: {item['secret_data_file']} {e}")
			continue
		if cluster not in grouped_secrets:
			grouped_secrets[cluster] = {}
		if vault_path not in grouped_secrets[cluster]:
			grouped_secrets[cluster][vault_path] = {}
		grouped_secrets[cluster][vault_path][item['secret_key']] = secret_value

	for cluster, secrets_dict in grouped_secrets.items():
		for v_path, secret_data in secrets_dict.items():
			if cluster in (""," "):
				print("No secret engine specified, please fix your yaml")
				exit(1)	
			print(f"  -> Writing {v_path} Keys: {list(secret_data.keys())} on {cluster}")
			parts = cluster.split('/',1)
			if len(parts) > 1 and parts[1]:
				v_path = os.path.join(parts[1], v_path)
			tmp_parts = parts[0] if parts[0].endswith('/') else f"{parts[0]}/"
			if(tmp_parts not in mount_point):
				client.sys.enable_secrets_engine(backend_type='kv',options={'version': '2'},path=tmp_parts)
				response = client.sys.list_mounted_secrets_engines()['data']
				mount_point = (sorted(response.keys()))
			client.secrets.kv.v2.create_or_update_secret(mount_point=parts[0] ,path=v_path,secret=secret_data)


def merge_structure(file):
	global final_structure
	def deep_merge(base_dict,update_dict):
		for key, value in update_dict.items():
			if (key in base_dict and 
				isinstance(base_dict[key], dict) and 
				isinstance(value, dict)):
				deep_merge(base_dict[key], value)
			else:
				base_dict[key] = value
		return base_dict
	with open(file) as f:
		main_conf = yaml.safe_load(f)
	files_to_merge = main_conf.get('conf',[])
	for file_path in files_to_merge:
		with open(file_path) as file:
			current_data = yaml.safe_load(file)
		deep_merge(base_dict=final_structure,update_dict=current_data)


merge_structure(main_config_file)
parser = argparse.ArgumentParser(description="HashiCorp Vault Tool")
subparsers = parser.add_subparsers(dest='command', required=True, help='Available commands')
parser_backup = subparsers.add_parser('backup', help='Backup logic')
parser_backup.add_argument('--src', required=True,help='Openshift / Master vault name')
parser_backup.add_argument('--dir', required=True,help='Dir for save secrets') 
parser_backup.set_defaults(func=handle_backup)
parser_sync = subparsers.add_parser('sync', help='Sync logic')
parser_sync.add_argument('--vault', dest="src",required=True,help='')
parser_sync.set_defaults(func=handle_sync)
parser_list = subparsers.add_parser('list', help='List on screen secrets')
parser_list.add_argument('--src',required=True,help='Openshift / Master vault name')
parser_list.add_argument('--cluster', help='Specify a cluster e.g: [ocp4]')
parser_list.add_argument('--inline', help='')
parser_list.add_argument('--dir',help='Destination for secrets')
parser_list.set_defaults(func=handle_list)
parser_import = subparsers.add_parser('import', help='Import Secrets')
parser_import.add_argument('--vault', dest="src",required=True,help='')
parser_import.set_defaults(func=handle_import)
args = parser.parse_args()
args.func(args)
