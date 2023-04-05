SmarterPlaylists

SmarterPlaylists is a modified version of the original SmarterPlaylists web application, created by user plamere. The application generates sophisticated playlists on Spotify. The modified version includes fixes to make it usable on the user's local machine.

Prerequisites
Python (2.7.18)
Nginx
Redis
Virtualenv
A Spotify Developer App API

To create a Spotify Developer App API, follow these steps:

Go to developer.spotify.com and log in with your Spotify account.
Click on the "Dashboard" link.
Click on "Create an App" and fill in the necessary information.
Once the app is created, note the Client ID and Client Secret values.
Add "http://localhost/auth.html" to the list of Redirect URIs.
Installation

Clone the SmarterPlaylists repository:

```
git clone https://github.com/declavea/SmarterPlaylists.git
```

Create a virtual environment:

```
virtualenv -p $(which python2) venv
```

Activate the virtual environment:

```
source venv/bin/activate
```

Install the required packages:

```
pip install -r ./SmarterPlaylists/requirements.txt
```

Configure the environment variables by editing the env.sh file:

```
cd SmarterPlaylists
vi env.sh
```

Add the following lines:

```
export SPOTIPY_CLIENT_ID=<your-client-id>
export SPOTIPY_CLIENT_SECRET=<your-client-secret>
export SPOTIPY_REDIRECT_URI=http://localhost/auth.html
export PBL_CACHE=REDIS
export MAX_TRACKS=10000
```

Replace <your-client-id> and <your-client-secret> with the values obtained from the Spotify Developer App API.

Source the env.sh file:

```
source env.sh
```

Change directory to the nginx folder in the project root directory:

```
cd nginx
```

Run the setup_nginx.sh script as sudo:

```
sudo ./setup_nginx.sh
```

Restart nginx:

```
sudo service nginx restart
```

Change directory to the Redis directory in the project root directory:

```
cd ../redis
```

Run the stop-redis script to kill any previous Redis instances:

```
./stop-redis
```

If there are any Redis instances still running, kill those PIDs manually with:

```
kill -9 <PID>
```

Start Redis by running the start-redis script:

```
./start-redis
```

Run the server:

```
nohup python scheduler.py 2>&1 1> scheduler.log &
nohup python flask_server.py 2>&1 1> flask_server.log &
```

To kill the scheduler:
```kill %1```

To kill the flask_server:
```kill %2```


Open a web browser and go to http://localhost. You should see the SmarterPlaylists home page.

Usage
```Log in with your Spotify account.
Select the playlist you want to modify.
Select the criteria you want to use to modify the playlist.
Click the "Create Playlist" button.
License

SmarterPlaylists is licensed under the MIT License.```
