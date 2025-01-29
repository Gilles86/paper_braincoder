docker run -i --rm \
	-v $basedir/BIDS:/bids_dataset \
	-v analyze-prfpy/default_config.yml:/config.yml \
	niklasmueller/prfanalyze-prfpy \
	/bids_dataset \
	/config.yml --participant_label 01