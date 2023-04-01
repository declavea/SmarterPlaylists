# Script to update web/main.js with the Spotify Client ID, which must be hardcoded.

# NOTE: 

source ../env.sh
web_path=$(dirname "$(pwd)")"/web"

if grep -q "SPOTIPY_CLIENT_ID" "$web_path/main.js"; then
     sed -i "s/SPOTIPY_CLIENT_ID/$SPOTIPY_CLIENT_ID/" $web_path/main.js
     echo "SUCCESS: "$web_path"/main.js has been updated with your SPOTTIFY_CLIENT_ID environment variable"
else
     echo "SKIPPED: "$web_path"/main.js already has the SPOTTIFY_CLIENT_ID value set"
fi

if grep -q "MAX_TRACKS" "$web_path/program.js"; then
     sed -i "s/MAX_TRACKS/$MAX_TRACKS/" $web_path/program.js
     echo "SUCCESS: "$web_path"/program.js has been updated with your MAX_TRACKS value"
else
     echo "SKIPPED: "$web_path"/program.js already has the MAX_TRACKS set"
fi
