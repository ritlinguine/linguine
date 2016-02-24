sudo pkill -9 node
sudo pkill -9 python

timestamp="$(date +'%m-%d-%Y-%T')"

#Rotate logs
cp /home/linguini/logs/node-latest /home/linguini/logs/node-$timestamp
cp /home/linguini/logs/python-latest /home/linguini/logs/python-$timestamp

#Run python process
cd /home/linguini/linguine-python
git pull
/home/linguini/.pyenv/versions/3.4.3/bin/python -u -m linguine.webserver > /home/linguini/logs/python-latest &

#Run Node process
cd /home/linguini/linguine-node
npm install
/home/linguini/node_modules/bower/bin/bower install
git pull

#Run JS process
node_modules/gulp/bin/gulp.js build
npm start > /home/linguini/logs/node-latest &
