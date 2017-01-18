#!/bin/bash

echo -e "use linguine-development\ndb.analyses.remove({\"result\":\"\"})"
echo -e "use linguine-production\ndb.analyses.remove({\"result\":\"\"})"
