"""Collection of file format converters."""

import mne
import logging
import mne_bids


def mne_conv(files, dst, **args):
    # Set conversion logging level
    verbose = args.get("logging", "INFO")

    # Set file reading preference
    reader = args.get("reader", mne.io.read_raw_egi)
    logging.info(f"Using {reader.__name__} for reading files")

    # Set power line frequency to default if not provided
    line_freq = args.get("line_freq", 50)
    logging.info(f"Using value of {line_freq} Hz for power line frequency")

    # Set overwrite preferences
    overwrite = args.get("overwrite", True)
    logging.info(f"Using overwrite = {overwrite} for conversion")

    # Set format preferences
    format = args.get("format", "auto")
    logging.info(f"Convertion will to {format} format")

    # Set event code mappings
    event_id = args.get("events_map", None)
    if not event_id:
        logging.info("Continuing without events code map")

    # Set BIDSPath map
    tag_map = args.get("tag_map", None)
    if not tag_map:
        logging.info("Using default tag map")
        tag_map = {
            "subject": "subject",
            "session": "session",
            "acquisition": "acquisition",
            "task": "task",
            "datatype": "datatype",
        }

    # Set anonymization strategy
    anonymize = args.get("anonymize", "default")
    if anonymize == "default":
        logging.info("Using default anonymization strategy")
        anonymize = {"daysback": 40000, "keep_his": False, "keep_source": False}

    if not anonymize:
        logging.info("Continuing without data anonymization")

    for file in files:
        raw = reader(file.path)
        raw.info["line_freq"] = line_freq

        # Form BIDSPath parameters from tag mapped_column
        path_params = {}
        for param, tag in tag_map.items():
            tag = file.tags.get(tag, None)
            path_params[param] = tag.value if tag else None
        path = mne_bids.BIDSPath(root=dst, **path_params)
        new_path = mne_bids.write_raw_bids(
            raw,
            path,
            event_id=event_id,
            anonymize=anonymize,
            format=format,
            overwrite=overwrite,
            verbose=verbose,
        )

        logging.info(f"Converted {path} and stored to {new_path}")
    logging.info(f"Conversion to {format} format complete")
