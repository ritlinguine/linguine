#!/bin/bash

echo -e "use linguine-development\ndb.analyses.find({\"result\":\"\"});" | mongo
echo -e "use linguine-production\ndb.analyses.find({\"result\":\"\"});" | mongo
