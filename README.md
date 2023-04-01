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

bash
Copy code
git clone https://github.com/declavea/SmarterPlaylists.git


Create a virtual environment:

bash
Copy code
virtualenv -p $(which python2) venv


Activate the virtual environment:

bash
Copy code
source venv/bin/activate


Install the required packages:

bash
Copy code
pip install -r ./SmarterPlaylists/requirements.txt


Configure the environment variables by editing the env.sh file:

bash
Copy code
cd SmarterPlaylists
vi env.sh


Add the following lines:

arduino
Copy code
export SPOTIPY_CLIENT_ID=<your-client-id>
export SPOTIPY_CLIENT_SECRET=<your-client-secret>
export SPOTIPY_REDIRECT_URI=http://localhost/auth.html
export PBL_CACHE=REDIS
export MAX_TRACKS=10000


Replace <your-client-id> and <your-client-secret> with the values obtained from the Spotify Developer App API.

Source the env.sh file:

bash
Copy code
source env.sh


Change directory to the nginx folder in the project root directory:

bash
Copy code
cd nginx


Run the setup_nginx.sh script as sudo:

bash
Copy code
sudo ./setup_nginx.sh


Restart nginx:

Copy code
sudo service nginx restart


Change directory to the Redis directory in the project root directory:

bash
Copy code
cd ../redis


Run the stop-redis script to kill any previous Redis instances:

arduino
Copy code
./stop-redis


If there are any Redis instances still running, kill those PIDs manually with:

bash
Copy code
kill -9 <PID>


Start Redis by running the start-redis script:

bash
Copy code
./start-redis


Run the server:

Copy code
python runserver.py


Open a web browser and go to http://localhost. You should see the SmarterPlaylists home page.

Usage
Log in with your Spotify account.
Select the playlist you want to modify.
Select the criteria you want to use to modify the playlist.
Click the "Create Playlist" button.
License

SmarterPlaylists is licensed under the MIT License.
