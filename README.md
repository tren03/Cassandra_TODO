A Todo app that uses a cassandra cluster with a single node in a local setting and stores a backup copy in mongo
Make sure to be running a local cluster of cassandra on your system.

I followed this tutorial for the installation - https://www.youtube.com/watch?v=pGhkX5z_vW8&list=PLalrWAGybpB-L1PGA-NfFu2uiWHEsdscD&index=4&ab_channel=jumpstartCS

(It's also a pretty good series on cassandra)

Note: During cassandra installation, I had to manually add the deb "http" blah blah link in the sources.list of my linux system, and then run sudo apt-get update

Run app.py in root directory of project
![image](https://github.com/tren03/Cassandra_TODO/assets/82367813/9ec52357-da58-49c8-b3f6-d6ebb9e2a78e)


![image](https://github.com/tren03/Cassandra_TODO/assets/82367813/43d8b0cf-0e4f-4878-9060-f317e6c481cc)


![image](https://github.com/tren03/Cassandra_TODO/assets/82367813/bcf97577-cef8-4f7d-8278-dc9dc4d37f70)


Cassandra running locally

![image](https://github.com/tren03/Cassandra_TODO/assets/82367813/650f301f-89e0-4e3a-ac7a-3af408114cbe)

Mongo backup

![image](https://github.com/tren03/Cassandra_TODO/assets/82367813/f15e0a8a-13f8-49ce-bb44-ad80490a5bae)

