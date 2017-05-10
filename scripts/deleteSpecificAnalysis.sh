#!/bin/sh

USER = ${1}
NAME = ${2}

echo -e "use linguine-development\ndb.analyses.remove({\"user_id\":db.users.findOne({\"dce\":\"\$USER\"})._id,\"analysis_name\":\"\$NAME\"})"
