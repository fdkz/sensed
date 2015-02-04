"""

TODO: save/load the stream?
TODO: make keyframe timestamps non-inclusive


random notes:
  when running the program, a selection box appears?
    load
    record

"""

import logging
llog = logging.getLogger(__name__) # the name 'log' is taken in sdl2

import time


class KeyframeSlot:
    def __init__(self, timestamp, keyframe, packets=None):
        self.timestamp = timestamp
        self.keyframe = keyframe
        # [(timestamp, packet), ..]
        self.packets = [] if packets == None else packets


class SyncBuffer:
    """ timesynchronize objects from in-order streams. add timestamp/stream_id/object triples, get timesorted objects back. """
    def __init__(self, sync_window_seconds=5.):
        """ sync_window_seconds - will only return entries that are older than this.
        if None, then return entries as soon as they arrive; no sorting. """
        self.sync_window_seconds = sync_window_seconds
        self.keyframeslots = [] # KeyframeSlot objects
        self.streams = {} # stream_id: packets_list

        # timepoints of sorted data. timestamps are read from the packets.
        self.start_time = None
        self.end_time = None # timestamp of the last sorted packet.
        self.current_time = None # will never go beyond the limits of start_time and end_time
        self.wanted_time = None # used by get_delta_packets(). like current_time, but can go beyond end_time and won't stop when there's no new packets for a while.

    def tick(self):
        """ Run the sorting algorithm on the received packets given to put_packet() """
        # get all older than sync_window_seconds packets and append them in order to the last keyframeslot packets-list.
        if not self.keyframeslots or not self.streams:
            return

        t = time.time()
        streams = self.streams.values()
        while 1:
            popstream = None
            poptime = None

            # find the oldest packet of any stream. stream is just a packet list.
            for stream in streams:
                if stream and (popstream == None or stream[0][0] < poptime):
                    popstream = stream
                    poptime = stream[0][0]

            # found the stream with the youngest packet.
            # remove the packet from sync-stream and append it to "keyframe" if the packet is sufficiently old.
            if popstream and (self.sync_window_seconds == None or t - poptime >= self.sync_window_seconds):
                    self.keyframeslots[-1].packets.append( popstream.pop(0) )
                    self.end_time = poptime
            else:
                break

    def put_keyframe(self, keyframe, timestamp=None):
        """ Sets the packet stream starting point and maybe also starts the recording process. Call periodically. """
        if self.start_time == None:
            assert timestamp != None
            self.start_time = timestamp
            self.end_time = timestamp
            # a little hack to not drop the first packet before using seek. Problem is that only the first time get_delta_packets
            # is called after the first packet/s, the first parameter to get_packets has to be inclusive. Too much work to do it so,
            # so we'll use this offset hack.
            self.current_time = timestamp - 0.00001
            self.wanted_time = timestamp

        if timestamp == None:
            timestamp = self.end_time + 0.00001

        if self.keyframeslots: # ensure timestamp is newer than previous
            assert self.keyframeslots[-1].timestamp < timestamp
        self.keyframeslots.append( KeyframeSlot(timestamp, keyframe) )

    def put_packet(self, timestamp, packet, stream_id):
        """ Add a packet to the SyncBuffer. SyncBuffer will decide if the packet is too old and disdcard it, or how to order it if not.
        This is not a general solution to the syncing problem - assumes that packets with the same stream_id are ordered. """
        if not self.keyframeslots:
            self.put_keyframe(None, timestamp)

        if timestamp >= self.start_time:
            stream = self.streams.get(stream_id, None)
            if not stream:
                stream = self.streams[stream_id] = []

            if stream:
                assert stream[-1][0] <= timestamp

            stream.append( (timestamp, packet) )

    def seek(self, timestamp):
        """ Set playback time (self.current_time) to timestamp. Clip time between available data (self.start_time and self.end_time).
        Return (keyframe, packet_list) that represent complete state of the system at the given time. Return (None, None) if no keyframe exists yet. """
        if self.start_time == None:
            return None, None
        else:
            timestamp = min(timestamp, self.end_time)
            timestamp = max(timestamp, self.start_time)
            self.current_time = timestamp
            self.wanted_time = timestamp
            keyframe, packet_list = self.get_seek_state(self.current_time)
            assert keyframe != None
            assert packet_list != None
            return keyframe, packet_list

    def get_delta_packets(self, dt):
        """ Move self.current_time forward by dt (if possible) and return packet_list [(timestamp, packet), ..] for that dt.
        self.current_time will be clipped by self.end_time. return empty list if no data yet.
        """
        if self.start_time == None or dt == 0.:
            return []
        else:
            assert self.current_time != None
            self.wanted_time += dt
            packet_list = self.get_packets(self.current_time, self.wanted_time)
            #llog.info("get from delta current_time %.3f wanted_time %.3f len %i", self.current_time, self.wanted_time, len(packet_list))
            self.current_time = min(self.wanted_time, self.end_time)
            return packet_list

    def get_current_time(self):
        """ Everything prior to this is set in stone in this SyncBuf. Changes only with self.seek and
        self.get_delta_packets and is always at least self.sync_window_seconds in the past.
        Returns None if no keyframe received yet with put_keyframe().
        Use this, or self.wanted_time as the current simulation time. self.wanted_time is smooth, but
        new packets can appear before it, and never before self.current_time. """
        return self.current_time

    #
    # lower-level functions
    #

    def get_prev_keyframe(self, timestamp):
        """ return the first (timestamp, keyframe) pair that came before the timestamp or at the exact timestamp.
        return (None, None) if timestamp is earlier than the first keyframe. """
        kfs, i = self._get_prev_keyframeslot(timestamp)
        if kfs:
            return kfs.timestamp, kfs.keyframe
        else:
            return None, None

    def _get_prev_keyframeslot(self, timestamp):
        """ Return (keyframeslot, index) - the first keyframeslot and its index in
        self.keyframeslots that came before the timestamp or at the exact timestamp.
        Return (None, None) if timestamp is earlier than the first keyframe or no keyframe exists yet. """
        for i, kf in enumerate(reversed(self.keyframeslots)):
            if kf.timestamp <= timestamp:
                return kf, len(self.keyframeslots) - i - 1
        # wanted timestamp is earlier than the first keyframe
        return None, None

    def get_packets(self, start_time, end_time, end_is_inclusive=True):
        """ return list of packets [(timestamp, packet), ..] between these timestamps. timestamps are relative to the SyncBuffer start.
        if end_is_inclusive is False, then start_time is inclusive. """
        assert end_time >= start_time

        # first, get keyframes that contain the start/end times.
        keyframeslot1, i1 = self._get_prev_keyframeslot(start_time)
        keyframeslot2, i2 = self._get_prev_keyframeslot(end_time)
        if keyframeslot1 == keyframeslot2:
            keyframeslot2 = None

        # for cache..
        #if self._prev_get_packets_end_time == start_time:
        #    pass
        #self._prev_get_packets_end_time = end_time

        result1 = result2 = []

        if end_is_inclusive:
            if keyframeslot1:
                # p[0] is timestamp, p[1] is packet. keyframeslot1 is a KeyframeSlot object.
                result1 = [p for p in keyframeslot1.packets if start_time < p[0] <= end_time]
            if keyframeslot2:
                result2 = [p for p in keyframeslot2.packets if start_time < p[0] <= end_time]
        else:
            if keyframeslot1:
                result1 = [p for p in keyframeslot1.packets if start_time <= p[0] < end_time]
            if keyframeslot2:
                result2 = [p for p in keyframeslot2.packets if start_time <= p[0] < end_time]

        result = result1

        # get full packets lists of keyframeslots that are between the edge slots.
        if i1 != None and i2 != None and i2 - i1 > 1:
            for kfs in self.keyframeslots[i1+1:i2]:
                result.extend(kfs.packets)

        result.extend(result2)

        return result

    def get_seek_state(self, timestamp):
        """ Return (keyframe, packet_list)
        Get keyframe and packets starting from that keyframe. The pair represents complete state of the system at the given time.
        Return (None, None) if timestamp is earlier than the first keyframe or no keyframe exists yet.
        timestamp is inclusive. """
        keyframeslot, i = self._get_prev_keyframeslot(timestamp)

        if keyframeslot == None:
            return None, None
        else:
            return keyframeslot.keyframe, [p for p in keyframeslot.packets if p[0] <= timestamp]

    def load_file(self, filename):
        """ load the whole file to ram """
        pass
