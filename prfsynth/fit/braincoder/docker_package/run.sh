export basedir="/data/ds-prfsynth"

docker run -i --rm \
	-v $basedir/BIDS:/bids_dataset \
	-v $(pwd)/default_config.yml:/config.yml \
    -v $(pwd)/entrypoint.sh:/entrypoint.sh \
    -v $(pwd)/run.py:/run.py \
    prfanalyze-braincoder \
	/bids_dataset \
	/config.yml --participant_label small