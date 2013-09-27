###############################################################################
# TDAF Services Keystone registration                                         #
###############################################################################

function get_id () {
    echo `"$@" | awk '/ id / { print $4 }'`
}
export ADMIN_PASSWORD=password
export OS_TENANT_NAME="admin"
export OS_USERNAME="admin"
export OS_PASSWORD="password"
export OS_AUTH_URL=http://192.168.56.101:5000/v2.0

ACCOUNTS_SERVICE=$(get_id keystone service-create \
    --name accounts \
    --type accounts \
    --description="TDAF Accounts Service")
keystone endpoint-create \
    --region RegionOne \
    --service_id $ACCOUNTS_SERVICE\
    --publicurl "http://127.0.0.1:20000/v1/%(tenant_id)s" \
    --adminurl "http://127.0.0.1:20000/v1/%(tenant_id)s" \
    --internalurl "http://127.0.0.1:20000/v1/%(tenant_id)s"

