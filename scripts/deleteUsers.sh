#!/bin/bash

function deleteUser {
    echo -e "use linguine-development\ndb.users.remove({\"dce\":\"$1\"})" | mongo
    echo ""
    echo -e "use linguine-production\ndb.users.remove({\"dce\":\"$1\"})" | mongo
    echo ""
}

if [ $# = 0 ]; then
    echo "You did not provide any arguments. To delete a specific user from the database, run:"
    echo "    ./purgeUserSpace.sh abc1234"
    echo "To delete all users, run:"
    echo "    ./purgeUserSpace.sh ALL"
else
    for var in $@
    do
        if [ $var = "ALL" ]; then
            read -e -p "Delete ALL users? (yes/NO)    " line
            if [[ $line != "yes" ]]; then
                echo ""
                echo "Aborting deletion of all users!"
                echo ""
            else
                echo ""
                echo "Deleting all users..."
                echo ""
                echo -e "use linguine-development\ndb.users.remove({})" | mongo
                echo ""
                echo -e "use linguine-production\ndb.users.remove({})" | mongo
            fi
        else
            echo "Deleting User: $var"
            echo ""
            deleteUser $var
            echo ""
        fi
    done
fi
