# README
Christoph Lechner, 3 June 2026

## Description
![system layout](doc/img/schematic.png)

### Technologies used
- OS: Ubuntu Server 24.04 LTS
- Docker
- PostgreSQL v18
- Python 3.10 or newer
  - notable packages used: FastAPI, scikit-learn, psycopg, pytest

## Motivation and Solution
The open-source project [CriticalMaps](https://www.criticalmaps.net/) ([repositories on github](https://github.com/criticalmaps/)) enables participants of ["Critical Mass"](https://en.wikipedia.org/wiki/Critical_Mass_(cycling)) events to share their current location with others on an interactive map.
Apps are available for the platforms iPhone and Android. Alternatively, you can see the current positions [online in the web browser](https://www.criticalmaps.net/map).

The CriticalMaps App (I only used the iOS version) is generally very well made.
There are however a few limitations that make catching up with a already on-going CM event quite challenging:
- The geoposition data provided by other users sharing their location is only refreshed every 60 seconds. So if your phone is not mounted to the handlebar of your bike, you have to frequently stop and wait until the map is updated.
- Often 'randomly distributed' dots can be seen on the map. These are the result of:
  - app users who just want to observe an on-going Critical Mass event in their city while they themselves are not participating. Specifically for this the app offers an observation mode, but people might either not be aware of this function or simply forget to switch it on
  - app users who are currently catching up with the Critical Mass, or who had to leave early
  - app users who are sharing their current location for other reasons (they do not intent to join a Critical Mass event)

### Applied solution
In the following we make the reasonable assumption that bike events such as a Critical Mass correspond to several moving dots in close proximity on the map. This assumption leads to the following data processing key steps:
- Identify "stationary devices", i.e. devices that haven't moved more than 100 meters in the last hour. These are likely app users who are just observing.
- Per default, these "stationary devices" are disregarded in the following.
- Then we run the [clustering algorithm](https://en.wikipedia.org/wiki/Cluster_analysis), currently [hierarchical clustering](https://en.wikipedia.org/wiki/Hierarchical_clustering) is used. The clustering algorithm has a configurable maximum distance to join a point to a cluster (or another point not yet part of a cluster). Only the current positions are taken into account for the clustering process.
- After this procedure, the dataset will exhibit this general structure:
  - There will be groups of points that are in close proximity.
  - On the other hand, some points are too far away from any other point. In this project, these are referred to as "single-point 'cluster'". For the following, they are not considered
- At the end of this process, the dataset is partitioned into several sets of points referred to as "clusters".

A reasonable starting point for selecting parameters could be
* minimum cluster size N=3 (one may consider to set this minimum threshold higher)
* radius 300m (at 15km/h 500m would correspond to 120s, so one position update may even be lost)
* ignore "stationary" devices (devices that did not move more than 100 meters in the previous hour)
* ignore "isolated" devices (devices that aren't part of any clusters)

### Examples
| A | B |
|---|---|
| ![](https://obj.clsrv.de/temp/IMG_1683_edited.png) | ![](https://obj.clsrv.de/temp/analysis__20260529T2050.png) |
| ![](https://obj.clsrv.de/temp/IMG_1691_s.png) | ![](https://obj.clsrv.de/temp/analysis__20260529T2236.png) |

## Running It
### Installation
There are two alternative ways to run the API data import:
* running it using Docker container
* installation in a fresh virtual environment

**Docker images**
There two `Dockerfile`s: one for API data import and one for the API server

**Installation in fresh virtual environment** using the commands:
```
$ python3 -m venv ./venv/
$ source ./venv/bin/activate
$ pip3 install -e .
[...]
```

Configuration of database access is done by adjusting the connection parameters in `./env` based on the template `./env.example` (you can test them using `check_db_conn.py`). Before running this project for the first time, the DB has to be prepared using the definitions in `schema.sql`.

### Running it
Then you can start to fill the database by running the API requestor `critical-dir-apiimport`. It periodically connects to the CriticalMaps API endpoint and stores the received information both in `.json` files and in the database.

For analysis of the stored data, there are currently two ways to run the software:
* To run the API server, either use the Docker image or run `critical-dir-api` in your virtual environment. See elsewhere in this document for documentation of URI structure and available API endpoints.
* For development, run the script `scripts/interactive_demo.py` on the command line. This script can serve as basis for your own analysis scripts.

### Organization of URIs
Currently the URIs on the HTTPS Apache2 server are organized as follows:
* `/myapp/`: top path used by the app, contains static materials, served by Apache2
* `/myapp/api/`: forwarded to FastAPI by Apache2 acting as reverse proxy for HTTPS termination
* `/myapp/api/objs/`: images generated by FastAPI go here, served by FastAPI

### API Endpoints
Here we list the provided API endpoints and the implemented HTTP method.
- `/location` (POST): This is the main end point to be called by the PWA/interactive web site.
- `/location_demo` (GET/POST): End point for demo purposes only, uses hardcoded geolocation in Hamburg, Germany. Does return JSON data.
- `/clusters` (GET): Get JSON data describing the identified clusters. Implemented for the implementation of (planned) interactive client programs.
- `/health` (GET): Health check URL. Is the API server reachable? This also performs a basic check of database 'freshness'. Returns HTTP status code 200 if checks are passed and HTTP status code 500 when something is out of order.
- `/inspect` (GET): (for development, disabled in normal operation) Used by the PWA/interactive website to see a cluster in more detail

## Data Downloader
The position data processed by this software project is periodically obtained from the CriticalMaps API.

For regular operation, Docker can be used. A `docker-compose.yaml` template file is available for customization. In addition, For building the Docker image, a `Dockerfile` is available. 

### Health Monitoring
The downloader supports HTTP Health Monitoring.
If you run it from the command line, pass the desired port to listen on to the program at start-up:
```
critical-dir-apiimport --status_port=22222
```

To check the health status of the data downloader, you can use `curl`.
The HTTP status code will be 200 if everything is ok, or 500 if no data could be downloaded for 900 seconds.
```
$ curl --head http://localhost:22222/check
```
In a production setting, this URL could be monitored with any URL monitor tool supporting GET or HEAD requests.
