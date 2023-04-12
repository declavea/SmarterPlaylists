SmarterPlaylists

SmarterPlaylists is a modified version of the original SmarterPlaylists web application, created by user plamere. The application generates sophisticated playlists on Spotify. The modified version includes fixes to make it usable on the user's local machine.

This branch is a Docker-zed version of the project for easier use and portability.

Steps to run:

1) Install Docker
2) Get a Spotify developer key at developer.spotify.com
  a) Copy your CLIENT_ID value
  b) Copy your CLIENT_SECRET value
  c) In the Redirect URIs section, add "http://localhost/auth.html"
3) Edit the [Projet Home]/.env file and replace the placeholders with your Spotify credentials
		SPOTIPY_CLIENT_ID=[place spotify client id here]
		SPOTIPY_CLIENT_SECRET=[place spotify secred here]
4) Edit the [Projecct_Home]/web/main.js file, and replace the Spotify_client id value
		line 7: var client_id = 'SPOTIPY_CLIENT_ID';
5) Edit the [Project_Home]/web/program.js file, and replace the MAX_TRACKS placeholder with the max number of tracks you want each playlist to have (10000 suggested)
6) Open a terminal or command line window and run the following command in the [Project_Home] root:
	docker-compose up
7) To close the app, hit CTRL-C to kill the processes, then run the command:
        docker-compose down

----------------

Note: If running in Windows, Hyper-V may pre-reserver certain port ranges that may cause the server to fail (such as binding to port 5000).
to get around this without uninstalling Hyper-V, just kill the "winnat" service before running the docker-compose up step, then restart it aftwerards.

net stop winnat
docker start ...
net start winnat
