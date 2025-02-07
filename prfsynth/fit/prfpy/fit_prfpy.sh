export basedir=/data/ds-prfsynth

CONFIG_FILE=$PWD/configs/default_config.json

docker run -i --rm \
	-v $basedir/BIDS:/bids_dataset \
	-v CONFIG_FILE:/config.yml \
	prfanalyze-prfpy \
	/bids_dataset \
	/config.yml --participant_label verysmall