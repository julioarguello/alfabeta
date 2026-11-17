#!/bin/zsh
# Spike S14 in Google Cloud (#166): the scripted sign-in from a Cloud Run job, read only, one run.
#
#   spikes/s14-cloud/cloud.sh setup <project>     APIs, the two secrets (asked, never echoed), the
#                                                 image (Cloud Build), a service account that reads
#                                                 only those two secrets, and the job (no retries)
#   spikes/s14-cloud/cloud.sh run <project>       one execution, waits for it, prints its log
#   spikes/s14-cloud/cloud.sh logs <project>      the last execution's log again
#   spikes/s14-cloud/cloud.sh teardown <project>  deletes the job, the image, the account and both secrets
#
# Claude wrote this; the family runs it (constitution III: Claude never starts the real sign-in, and
# the secrets go from the family's keyboard to Secret Manager without touching the Mac's disk, II).
# Uses the gcloud configuration S14_GCLOUD_CONFIG (default: losfueros) without changing the active one.
set -eu

PROJECT="${2:-}"
[[ -n "$PROJECT" ]] || { print -u2 "usage: $0 setup|run|logs|teardown <project>"; exit 2; }
REGION="${S14_REGION:-europe-southwest1}"  # Madrid: the sign-in comes from Spain, as the student's does
JOB=alfabeta-s14
SA="$JOB@$PROJECT.iam.gserviceaccount.com"
REPO="$REGION-docker.pkg.dev/$PROJECT/alfabeta-spikes"
IMAGE="$REPO/s14:poc"
HERE="${0:A:h}"
g() { gcloud --configuration="${S14_GCLOUD_CONFIG:-losfueros}" --project="$PROJECT" --quiet "$@"; }

secret() {  # $1 secret name, $2 prompt; the value is read silently and piped straight to Secret Manager
  local value
  if ! g secrets describe "$1" >/dev/null 2>&1; then
    g secrets create "$1" --replication-policy=user-managed --locations="$REGION" >/dev/null
  fi
  read -rs "value?$2: "; print
  print -rn -- "$value" | g secrets versions add "$1" --data-file=- >/dev/null
  unset value
  g secrets add-iam-policy-binding "$1" --member="serviceAccount:$SA" --role=roles/secretmanager.secretAccessor >/dev/null
  print "secret $1: stored"
}

case "$1" in
  setup)
    g services enable run.googleapis.com secretmanager.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com
    g iam service-accounts describe "$SA" >/dev/null 2>&1 ||
      g iam service-accounts create "$JOB" --display-name="alfabeta spike S14 (reads two secrets only)"
    secret alfabeta-s14-account "Cuenta del cole (correo)"
    secret alfabeta-s14-password "Contraseña de la cuenta del cole"
    g artifacts repositories describe alfabeta-spikes --location="$REGION" >/dev/null 2>&1 ||
      g artifacts repositories create alfabeta-spikes --repository-format=docker --location="$REGION"
    cp "$HERE/../s14_scripted_signin.py" "$HERE/s14_scripted_signin.py"
    g builds submit "$HERE" --region="$REGION" --tag="$IMAGE"
    rm -f "$HERE/s14_scripted_signin.py"
    g run jobs deploy "$JOB" --region="$REGION" --image="$IMAGE" --service-account="$SA" \
      --set-secrets=S14_ACCOUNT=alfabeta-s14-account:latest,S14_PASSWORD=alfabeta-s14-password:latest \
      --max-retries=0 --task-timeout=300 --memory=2Gi --cpu=1
    print "setup done: now  $0 run $PROJECT"
    ;;
  run)
    g run jobs execute "$JOB" --region="$REGION" --wait || true
    "$0" logs "$PROJECT"
    ;;
  logs)
    g logging read "resource.type=cloud_run_job AND resource.labels.job_name=$JOB" \
      --freshness=1h --order=asc --format="value(textPayload)" | grep -v '^$'
    ;;
  teardown)
    g run jobs delete "$JOB" --region="$REGION" || true
    g artifacts repositories delete alfabeta-spikes --location="$REGION" || true
    g secrets delete alfabeta-s14-password || true
    g secrets delete alfabeta-s14-account || true
    g iam service-accounts delete "$SA" || true
    ;;
  *) print -u2 "usage: $0 setup|run|logs|teardown <project>"; exit 2;;
esac
