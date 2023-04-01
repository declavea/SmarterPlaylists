# Note, this script requires being run as sudo, in order to copy the confg file int /etc/nginx/conf.d

web_path=$(dirname "$(pwd)")"/web"

# using ? instead of / in the folling sed since pwd output will also contain back slashes
sed -e"s?WEB_PATH?$web_path?" ./smarterplaylists.conf > /etc/nginx/conf.d/smarterplaylists.conf
