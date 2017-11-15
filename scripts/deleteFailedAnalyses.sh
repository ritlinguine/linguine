#!/bin/bash

echo -e "use linguine-development\ndb.analyses.remove({\"result\":\"\"});" | mongo
echo -e "use linguine-production\ndb.analyses.remove({\"result\":\"\"});" | mongo
