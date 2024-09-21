import traceback

class ExceptionWrapper(Exception):
    """
    A class used to wrap exceptions with additional information.

    Attributes
    ----------
    debug : bool
        A flag indicating whether debug mode is enabled. (If not, a helpful message
        about how to enable a full traceback and/or more verbosity in the error
        reporting. Default is False.
    """
    debug = False
    def __init__(self,msg,e):
        """
        Initialize the ExceptionWrapper instance.

        Parameters
        ----------
        msg : str
            The message to include in the error.
        e : Exception
            The exception to wrap.
        """
        cause = e
        tb = cause.__traceback__
        tbdump = traceback.extract_tb(tb)
        if len(tbdump) > 1:
            if tbdump[0].filename == tbdump[-1].filename:
                edata = " ("+str(tbdump[0].filename)+" line:"+str(tbdump[0].lineno)+" triggered at line: "+str(tbdump[-1].lineno)+")."
            else:
                edata = " ("+str(tbdump[0].filename)+" line "+str(tbdump[0].lineno)+" triggered in: "+str(tbdump[-1].filename)+" at line "+str(tbdump[-1].lineno)+")."
        else:
            edata = " ("+str(tbdump[0].filename)+" line "+str(tbdump[0].lineno)+")."
        if isinstance(e, ExceptionWrapper):
            self.messages = [msg + edata] + e.messages
        elif type(e) == Exception:
            self.messages = [msg, str(cause) + edata]
        else:
            self.messages = [msg, type(cause).__name__+": "+str(cause) + edata]
        full_message = msg +". Error details:\n- "+("\n- ".join(self.messages[1:]))+"\n"
        if not self.debug:
            full_message += "\nAdd command line argument -d for a full traceback or one or more -v for higher verbosity."
        super().__init__(full_message)
