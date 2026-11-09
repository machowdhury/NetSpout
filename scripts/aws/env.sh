# Source this file. Nothing here creates anything. Required: P17_REGION=ca-central-1 (the only region authorized for this run).
: "${P17_REGION:?set P17_REGION=ca-central-1}"
[ "$P17_REGION" = ca-central-1 ] || { echo "this run is authorized for ca-central-1 only (got $P17_REGION)"; return 1 2>/dev/null || exit 1; }
export AWS_PAGER="" AWS_REGION=$P17_REGION AWS_DEFAULT_REGION=$P17_REGION
export AWS_PROFILE=${AWS_PROFILE:-default}
export P17_RUN=${P17_RUN:-p17-native-$(date -u +%Y%m%d)}
export P17_STATE=${P17_STATE:-$HOME/netspout/p17-aws/$P17_RUN.state}        # resource IDs created by 01_create.sh; cleanup deletes ONLY what is listed here
export P17_INSTANCE_TYPE=${P17_INSTANCE_TYPE:-m6i.2xlarge} P17_VOLUME_GIB=${P17_VOLUME_GIB:-150}
export P17_DEADMAN_MIN=${P17_DEADMAN_MIN:-600}                              # the instance powers itself off (and, with terminate-on-shutdown, is deleted) after this many minutes
export P17_REPO=${P17_REPO:-/Users/mahamudc/netspout/phase17-wt}
export P17_APPROVED_COMMIT=${P17_APPROVED_COMMIT:-91af353d1e9897e587e819002de65310de3b1640}   # source commit of the approved artifact (PR #11)
export P17_EXPECTED_GZ=${P17_EXPECTED_GZ:-4bf1d21469f5e699069797d654f7ccc57e00fbcade9b9304dcccdab2bd33be40}
export P17_EXPECTED_TAR=${P17_EXPECTED_TAR:-99c23bbb3f982456e03a38327f96d0050400d825ea534327d5925296a3cf5da3}
export P17_BASELINE_SPL=${P17_BASELINE_SPL:-/Users/mahamudc/netspout/p17/appinspect/baseline_netspout.spl}   # released v2.0.1 netspout.spl
export P17_BASELINE_SHA=53f09e5f8c16e6615ecd9c73c0504e9ac938fa28b0029313384be5f09105ff17
export P17_IMG_PRIMARY=${P17_IMG_PRIMARY:-splunk/splunk:10.6.1@sha256:2a7cf9d2e8a2226773a9fac95b5e0e2cc8752496abfb134a21bdf8f67c9ee44d}   # Splunk 10.6.1.1
export P17_SUSTAIN_PRIMARY=${P17_SUSTAIN_PRIMARY:-3600}
mkdir -p "$(dirname "$P17_STATE")"; touch "$P17_STATE"
[ -f "$P17_STATE" ] && . "$P17_STATE"
tag() { echo "ResourceType=$1,Tags=[{Key=Name,Value=$P17_RUN},{Key=Project,Value=netspout-phase17},{Key=Disposable,Value=true},{Key=splunkit_data_classification,Value=private},{Key=splunkit_environment_type,Value=non-prd}]"; }   # the two splunkit_* tags are required by the organization policy
