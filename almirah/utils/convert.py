"""File format conversion utility functions."""

import os
import shlex
import logging

from .gen import run_shell


def dcm2nii(files, out, dst, **kwargs):
    """
    Convert DICOM files to NIfTI and write to disk.

    Parameters
    ----------
    files : List of Files
        List of File objects that represent the files to be converted.
    out : str
        Output format desired.
    dst: Layout
        Destination layout where converted files will be stored.
    config: str
        Path to config file. Should be compatible with dcm2bids
        version installed.

    Returns
    -------
    None
    """

    # Set and build command
    flags = kwargs.get("flags", None)
    tmp = [
        "dcm2bids",
        "-d",
        "{path}",
        "-p",
        "{subject}",
        "-s",
        "{session}",
        "-c",
        "{config}",
        "-o",
        "{dst}",
        "-l",
        "{verbose}",
    ]
    if flags and not flags.issubset(_DCM2NII_VALID_FLAGS):
        raise ValueError(
            "Unsupported flag found \n"
            f"Valid flags: {','.join(_DCM2NII_VALID_FLAGS)}",
        )
    if flags:
        tmp.extend(flags)
    tmp = shlex.join(tmp)

    # Set logging level
    verbose = kwargs.get("logging", "INFO")

    # Set configuration file
    config = kwargs.get("config", None)
    if not config:
        raise KeyError("Expected config path, but not found")

    # Set argument mappping
    tag_map = kwargs.get("tag_map", None)
    if not tag_map:
        logging.info("Using default tag map")
        tag_map = {"subject": "subject", "session": "session"}

    logging.info(f"Using command template: {tmp}")

    for file in files:
        # Fill command with arguments
        args = {}
        for param, tag in tag_map.items():
            tag = file.tags.get(tag, None)
            if tag:
                args[param] = tag.value
        args["path"] = file.path
        cmd = tmp.format(**args, dst=dst.root, verbose=verbose, config=config)
        run_shell(cmd)
        logging.info(f"Converted {file.path} and stored to {dst.root}")
    logging.info("Conversion to nii complete")


def edf2asc(files, out, dst, **kwargs):
    """Convert Eye track data format and write to disk."""

    # Set and build command
    tmp = ["edf2asc", "{path}", "{new_path}"]
    flags = kwargs.get("flags", None)
    if flags and not flags.issubset(_EDF2ASC_VALID_FLAGS):
        raise ValueError(
            "Unsupported flag found. \n"
            f"Valid flags: {', '.join(_EDF2ASC_VALID_FLAGS)}"
        )
    if flags:
        tmp.extend(flags)
    tmp = shlex.join(tmp)

    logging.info(f"Using command template: {tmp}")

    for file in files:
        # Fill command with arguments
        args = {}
        new_tags = {k: v for k, v in file.tags.items()}
        new_tags.update({"extension": "asc", "sourcetype": "None"})
        new_path = os.path.join(
            dst.root, dst.specification.build_path(False, **new_tags)
        )

        args["path"] = file.path
        args["new_path"] = new_path
        os.makedirs(os.path.dirname(new_path), exist_ok=True)

        cmd = tmp.format(**args)
        run_shell(cmd)

        logging.info(f"Converted {file.path} and stored to {new_path}")
    logging.info("Conversion to asc complete")


def nirx2snirf(files, out, dst, **kwargs):
    """Convert NIRS data format and write to disk."""

    import mne
    import mne_nirs

    for file in files:
        raw = mne.io.read_raw_nirx(file.path)
        raw.anonymize(**kwargs.get("anonymize", {}))

        new_tags = {k: v for k, v in file.tags.items()}
        new_tags.update({"extension": "snirf", "sourcetype": "None"})
        new_path = os.path.join(
            dst.root, dst.specification.build_path(False, **new_tags)
        )

        os.makedirs(os.path.dirname(new_path), exist_ok=True)
        mne_nirs.io.write_raw_snirf(raw, new_path)
        logging.info(f"Converted {file.path} and stored to {new_path}")
    logging.info("Conversion to snirf complete")


def eeg_converter(files, out, dst, **kwargs):
    """Convert EEG data format and write to disk."""

    import mne
    import mne_bids

    # Set conversion logging level
    verbose = kwargs.get("logging", "INFO")

    # Set power line frequency to default if not provided
    line_freq = kwargs.get("line_freq", 50)
    logging.info(f"Using value of {line_freq} Hz for power line frequency")

    # Set BIDSPath map
    tag_map = kwargs.get("tag_map", None)
    if not tag_map:
        logging.info("Using default tag map")
        tag_map = {
            "subject": "subject",
            "session": "session",
            "acquisition": "acquisition",
            "task": "task",
            "datatype": "datatype",
            "run": "run",
            "suffix": "suffix",
        }

    # Set overwrite preferences
    overwrite = kwargs.get("overwrite", True)
    logging.info(f"Using overwrite = {overwrite} for conversion")

    # Set format preferences
    logging.info(f"Convertion will be to {out} format")

    # Set event code mappings
    event_id = kwargs.get("events_map", None)
    if not event_id:
        logging.info("Continuing without events code map")

    # Set anonymization strategy
    anonymize = kwargs.get("anonymize", None)
    if not anonymize:
        logging.info("Continuing without data anonymization")
    else:
        logging.info(f"Using daysback of {anonymize['daysback']} to anonymize")

    for file in files:
        raw = mne.io.read_raw(file.path)
        raw.info["line_freq"] = line_freq

        # Form BIDSPath parameters from tag mapped_column
        path_params = {}
        for param, tag in tag_map.items():
            tag = file.tags.get(tag, None)
            path_params[param] = tag if tag else None

        path = mne_bids.BIDSPath(root=dst.root, **path_params)

        mne_bids.write_raw_bids(
            raw,
            path,
            event_id=event_id,
            anonymize=anonymize,
            format=out,
            overwrite=overwrite,
            verbose=verbose,
        )

        logging.info(f"Converted {file.path} and stored to {path}")
    logging.info(f"Conversion to {out} format complete")


def convert(files, out, dst, **kwargs):
    """Convert a file collection from one format to another."""

    # Proceed only if all files have the same extension
    extension = set()
    for file in files:
        extension.add(file.tags.get("extension"))
    if len(extension) > 1:
        raise TypeError(
            "Expected all files of same extension, but received different \n"
            f"Found {len(extension)}: {', '.join(extension)}",
        )

    # Check if output format supported and choose converter
    extension = extension.pop()
    for outs in _SUPPORTED:
        if out in outs and extension in _SUPPORTED[outs]["from"]:
            converter = _SUPPORTED[outs]["using"]
            break

    if not converter:
        raise ValueError(f"Extension {extension} or output {out} mismatch.")

    if not dst or dst == "":
        raise ValueError("Expected valid destination path, received empty")

    # Initiate conversion
    logging.info(f"Converting {extension} to {out} using {converter.__name__}")
    converter(files, out, dst, **kwargs)


_SUPPORTED = {
    (
        "BrainVision",
        "EDF",
        "FIF",
        "auto",
    ): {
        "from": (
            ".bdf",
            ".cnt",
            ".data",
            ".edf",
            ".gdf",
            ".mat",
            ".mff",
            ".nxe",
            ".set",
            ".vhdr",
        ),
        "using": eeg_converter,
    },
    ("ASCII",): {"from": (".edf",), "using": edf2asc},
    ("NIfTI",): {"from": (".dcm",), "using": dcm2nii},
    ("SNIRF",): {"from": (".nirx",), "using": nirx2snirf},
}
_DCM2NII_VALID_FLAGS = {"--forceDcm2niix", "--clobber"}
_EDF2ASC_VALID_FLAGS = {
    "-t",
    "-c",
    "-z",
    "-v",
    "-y",
    "-sp",
    "-sh",
    "-sg",
    "-l",
    "-nr",
    "-r",
    "-nl",
    "-res",
    "-vel",
    "fvel",
    "-s",
    "-ne",
    "-e",
    "-ns",
    "-nv",
    "-nst",
    "-nmsg",
    "-neye",
    "-nflags",
    "-hpos",
    "-avg",
    "-ftime",
    "-input",
    "-buttons",
    "-failsafe",
    "-ntarget",
    "-ntime_check",
    "-npa_check",
    "-logmsg",
}
