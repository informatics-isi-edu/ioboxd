from ioboxd.core import *
from ioboxd.providers.export.api import check_access


class ExportRetrieve (RestHandler):

    def __init__(self):
        RestHandler.__init__(self)

    def send_log(self, file_path):
        web.ctx.ioboxd_content_type = 'text/plain'
        web.header('Content-Type', web.ctx.ioboxd_content_type)
        return self.get_content(file_path, web.ctx.webauthn2_context)

    def send_content(self, file_path):
        web.ctx.ioboxd_content_type = 'application/octet-stream'  # should eventually try to be more specific here
        web.header('Content-Type', web.ctx.ioboxd_content_type)
        web.header('Content-Disposition', "filename*=UTF-8''%s" % urllib.quote(os.path.basename(file_path)))
        return self.get_content(file_path, web.ctx.webauthn2_context)

    @web_method()
    def GET(self, key, requested_file=None):
        export_dir = os.path.abspath(os.path.join(STORAGE_PATH, key))
        if not os.path.isdir(export_dir):
            raise NotFound("The resource %s does not exist. It was never created or has been deleted." % key)
        if not check_access(export_dir):
            return Forbidden("The currently authenticated user is not permitted to access the specified resource.")

        for dirname, dirnames, filenames in os.walk(export_dir):

            # first, deal with the special case "metadata" files...
            if ".access" in filenames:
                filenames.remove(".access")
            log_path = os.path.abspath(os.path.join(dirname, ".log"))
            if ".log" in filenames:
                if requested_file and requested_file == 'log':
                    return self.send_log(log_path)
                filenames.remove(".log")

            # if there are no remaining files in the dir list, we don't have anything to reply with.
            # so, raise a 404 but also try to send back the log (if it exists) as additional diagnostic info.
            if not filenames:
                log_text = 'No additional diagnostic information available.\n'
                if os.path.isfile(log_path):
                    with open(log_path) as log:
                        log_text = log.read()
                raise NotFound(log_text)
            else:
                # otherwise we've got at least one file to reply with...
                for filename in filenames:
                    file_path = os.path.abspath(os.path.join(dirname, filename))
                    if not requested_file:
                        # if there is more than one file in the resource bucket and the caller wasn't explicit about
                        # which one to retrieve, it is a bad request.
                        if filenames.__len__() > 1:
                            raise BadRequest("The resource %s contains more than one file, it is therefore necessary "
                                             "to specify a filename in the request URL." % key)
                        else:
                            return self.send_content(file_path)
                    else:
                        # otherwise keep looping until we find a match
                        if requested_file == filename:
                            return self.send_content(file_path)
                        else:
                            continue

        # if we got here it means the caller asked for something that does not exist.
        raise NotFound("The requested file \"%s\" does not exist." % requested_file)
