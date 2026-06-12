CL, 07.06.2026

## Setting up system accounts and directories for data storage
```
cl@clsrv:~$ sudo useradd -m -c "user for cdir data storage" -s /bin/bash cdirdata
cl@clsrv:~$ sudo useradd -m -c "user for cdir proj" -s /bin/bash cdirproj
```

The following commands were used to prepare the top directory for data storage.
Here, the ingestion program generates new directories.
```
cl@clsrv:/srv$ sudo mkdir /srv/criticaldir_data
cl@clsrv:/srv$ sudo chown cdirdata:cdirdata /srv/criticaldir_data
cl@clsrv:/srv$ ls -ld /srv/criticaldir_data
drwxr-xr-x 2 cdirdata cdirdata 4096 Jun  7 13:17 /srv/criticaldir_data
```

## Preparation of DB access
This guide assumes that you have a running postgres database in your local network (or on the same machine...).
We create a new database and add one user for write access (mainly used for loading data into the DB) and one user for read-only access (used by analysis scripts, APIs, etc.).
Connect to the DB using the admin user (in my case `postgres`).
```
postgres> CREATE USER criticaldir WITH PASSWORD 'your_password';
CREATE ROLE
Time: 0.026s
postgres> CREATE DATABASE criticaldir OWNER criticaldir;
CREATE DATABASE
Time: 0.229s
postgres> CREATE USER criticaldir_ro WITH PASSWORD 'your_ro_password';
CREATE ROLE
Time: 0.013s
postgres> GRANT CONNECT ON DATABASE criticaldir TO criticaldir_ro;
GRANT
Time: 0.006s
postgres> \c criticaldir
You are now connected to database "criticaldir" as user "postgres"
Time: 0.022s
criticaldir> GRANT USAGE ON SCHEMA public TO criticaldir_ro;
GRANT
Time: 0.008s
criticaldir> GRANT SELECT ON ALL TABLES IN SCHEMA public TO criticaldir_ro;
GRANT
Time: 0.002s
criticaldir>
```
Above commands granted SELECT permission to `criticaldir_ro` on all tables that are already existing in database `criticaldir`. What is still missing is adjusting the permissions for tables that will be created in the future. As user `criticaldir` will be creating all the tables in the database `criticaldir`, the following command must be executed as user `criticaldir` **(not as superuser 'postgres')**:
```
criticaldir> ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO
  criticaldir_ro;
You're about to run a destructive command.
Do you want to proceed? [y/N]: y
Your call!
ALTER DEFAULT PRIVILEGES
Time: 0.009s
```
The database schema can be prepared by loading the contents of `schema.sql` (used version as in git commit id 6e83473):
```
criticaldir> \i doc/schema.sql
CREATE TABLE
CREATE INDEX
CREATE INDEX
CREATE INDEX
Time: 0.040s
criticaldir>
```

To activate the `earthdistance` extension, we have to connect to the DB as user `postgres`:
```
cl@clpc:~/work/criticalmaps--richtungspfeil$ pgcli -h 192.168.2.253 -p 15432 -u postgres -d criticaldir
Password for postgres: 
Using local time zone Europe/Berlin (server uses Etc/UTC)
Use `set time zone <TZ>` to override, or set `use_local_timezone = False` in the config
Server: PostgreSQL 18.0 (Debian 18.0-1.pgdg13+3)
Version: 4.5.0
Home: https://pgcli.com
criticaldir> CREATE EXTENSION cube;
CREATE EXTENSION
Time: 0.027s
criticaldir> CREATE EXTENSION earthdistance;
CREATE EXTENSION
Time: 0.014s
criticaldir>                                                                    
Goodbye!
```


```
cl@clsrv:/srv$ sudo -i
root@clsrv:~# su - cdirdata
cdirdata@clsrv:~$ mkdir prod
cdirdata@clsrv:~$ cd prod
cdirdata@clsrv:~/prod$ git clone https://github.com/christoph-lechner/critical-dir.git
Cloning into 'critical-dir'...
Username for 'https://github.com': christoph-lechner
Password for 'https://christoph-lechner@github.com': 
remote: Enumerating objects: 410, done.
remote: Counting objects: 100% (410/410), done.
remote: Compressing objects: 100% (197/197), done.
remote: Total 410 (delta 242), reused 364 (delta 196), pack-reused 0 (from 0)
Receiving objects: 100% (410/410), 235.14 KiB | 3.85 MiB/s, done.
Resolving deltas: 100% (242/242), done.
cdirdata@clsrv:~/prod$ cd critical-dir/
cdirdata@clsrv:~/prod/critical-dir$ git checkout cl_20260604__docker 
branch 'cl_20260604__docker' set up to track 'origin/cl_20260604__docker'.
Switched to a new branch 'cl_20260604__docker'
cdirdata@clsrv:~/prod/critical-dir$
```


Configuration in `.env` file. Moved the `.env` file into the home directory of the account to avoid overwriting it when updating the code repository.
- Created the directory for temporary objects (only used by API server): `/srv/criticaldir_data/tempobjs/`
- adjusted UID/GID in `docker-compose.yaml` to match values of user `cdirdata`.
- adjusted directory mapping of `/app/cmdata`
- adjusted port mapping of status port

**Add contents of .env file here**

**The first version deployed on `clsrv` using Docker is git commit id 944fdf0.**

For the case one wants to access the DB using the `pgcli` tool, I also created a new file `~/.pgpass` to hold the DB access credentials (be sure to use mode 600, otherwise the DB clients ignore the `~/.pgpass` file):
```
cdirdata@clsrv:~/prod/critical-dir$ vim ~/.pgpass
cdirdata@clsrv:~/prod/critical-dir$ touch ~/.pgpass
cdirdata@clsrv:~/prod/critical-dir$ chmod 600 ~/.pgpass
cdirdata@clsrv:~/prod/critical-dir$ $YOUR_FAVORITE_EDITOR ~/.pgpass
```
