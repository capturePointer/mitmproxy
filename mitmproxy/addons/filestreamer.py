import os.path

from mitmproxy import exceptions
from mitmproxy import flowfilter
from mitmproxy import io


class FileStreamer:
    def __init__(self):
        self.stream = None
        self.filt = None
        self.active_flows = set()  # type: Set[flow.Flow]

    def start_stream_to_path(self, path, mode, flt):
        path = os.path.expanduser(path)
        try:
            f = open(path, mode)
        except IOError as v:
            raise exceptions.OptionsError(str(v))
        self.stream = io.FilteredFlowWriter(f, flt)
        self.active_flows = set()

    def configure(self, options, updated):
        # We're already streaming - stop the previous stream and restart
        if "filtstr" in updated:
            if options.get("filtstr"):
                self.filt = flowfilter.parse(options.filtstr)
                if not self.filt:
                    raise exceptions.OptionsError(
                        "Invalid filter specification: %s" % options.filtstr
                    )
        if "outfile" in updated:
            if self.stream:
                self.done()
            if options.outfile:
                path, mode = options.outfile
                if mode not in ("wb", "ab"):
                    raise exceptions.OptionsError("Invalid mode.")
                self.start_stream_to_path(path, mode, self.filt)

    def tcp_start(self, flow):
        if self.stream:
            self.active_flows.add(flow)

    def tcp_end(self, flow):
        if self.stream:
            self.stream.add(flow)
            self.active_flows.discard(flow)

    def response(self, flow):
        if self.stream:
            self.stream.add(flow)
            self.active_flows.discard(flow)

    def request(self, flow):
        if self.stream:
            self.active_flows.add(flow)

    def done(self):
        if self.stream:
            for flow in self.active_flows:
                self.stream.add(flow)
            self.active_flows = set([])
            self.stream.fo.close()
            self.stream = None
