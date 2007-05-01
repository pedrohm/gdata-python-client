#!/usr/bin/python
#
# Copyright (C) 2006 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""AtomService provides CRUD ops. in line with the Atom Publishing Protocol.

  AtomService: Encapsulates the ability to perform insert, update and delete
               operations with the Atom Publishing Protocol on which GData is
               based. An instance can perform query, insertion, deletion, and
               update.
"""

__author__ = 'api.jscudder (Jeffrey Scudder)'

import httplib
import urllib
import re
import base64
try:
  from xml.etree import ElementTree
except ImportError:
  from elementtree import ElementTree

URL_REGEX = re.compile('http(s)?\://([\w\.-]*)(\:(\d+))?(/.*)?')

class AtomService(object):
  """Performs Atom Publishing Protocol CRUD operations."""

  # Default values for members
  port = 80
  ssl = False

  def __init__(self, server=None, additional_headers=None):
    """Creates a new AtomService client.
    
    Args:
      server: string (optional) The start of a URL for the server
              to which all operations should be directed. Example: 
              'www.google.com'
      additional_headers: dict (optional) Any additional HTTP headers which
                          should be included with CRUD operations.
    """

    self.server = server
    self.additional_headers = additional_headers or {}

    self.additional_headers['User-Agent'] = 'Python Google Data Client Lib'

  def _ProcessUrl(self, url):
    """Processes a passed URL.  If the URL does not begin with https?, then
    the default value for self.server is used"""

    server = self.server
    port = self.port
    ssl = self.ssl
    uri = url

    m = URL_REGEX.match(url)

    if m is None:
      return (server, port, ssl, uri)
    else:
      if m.group(1) is not None:
        port = 443
        ssl = True
      if m.group(3) is None:
        server = m.group(2)
      else:
        server = m.group(2)
        port = int(m.group(4))
      if m.group(5) is not None:
        uri = m.group(5)
      else:
        uri = '/'
      return (server, port, ssl, uri)

  def UseBasicAuth(self, username, password):
    """Sets an Authenticaiton: Basic HTTP header containing plaintext.
    
    The username and password are base64 encoded and added to an HTTP header
    which will be included in each request. Note that your username and 
    password are sent in plaintext.

    Args:
      username: str
      password: str
    """

    base_64_string = base64.encodestring('%s:%s' % (username, password))
    base_64_string = base_64_string.strip()
    self.additional_headers['Authorization'] = 'Basic %s' % (base_64_string,)
    
  def _CreateConnection(self, uri, http_operation, extra_headers=None,
      url_params=None, escape_params=True):
      
    full_uri = BuildUri(uri, url_params, escape_params)
    (server, port, ssl, full_uri) = self._ProcessUrl(full_uri)

    if ssl:
      connection = httplib.HTTPSConnection(server, port)
    else:
      connection = httplib.HTTPConnection(server, port)

    connection.putrequest(http_operation, full_uri)

    if isinstance(self.additional_headers, dict):
      for header in self.additional_headers:
        connection.putheader(header, self.additional_headers[header])
    if isinstance(extra_headers, dict):
      for header in extra_headers:
        connection.putheader(header, extra_headers[header])
    connection.endheaders()
    
    return connection

  # CRUD operations
  def Get(self, uri, extra_headers=None, url_params=None, escape_params=True):
    """Query the APP server with the given URI

    The uri is the portion of the URI after the server value 
    (server example: 'www.google.com').

    Example use:
    To perform a query against Google Base, set the server to 
    'base.google.com' and set the uri to '/base/feeds/...', where ... is 
    your query. For example, to find snippets for all digital cameras uri 
    should be set to: '/base/feeds/snippets?bq=digital+camera'

    Args:
      uri: string The query in the form of a URI. Example:
           '/base/feeds/snippets?bq=digital+camera'.
      extra_headers: dicty (optional) Extra HTTP headers to be included
                     in the GET request. These headers are in addition to 
                     those stored in the client's additional_headers property.
                     The client automatically sets the Content-Type and 
                     Authorization headers.
      url_params: dict (optional) Additional URL parameters to be included
                  in the query. These are translated into query arguments
                  in the form '&dict_key=value&...'.
                  Example: {'max-results': '250'} becomes &max-results=250
      escape_params: boolean (optional) If false, the calling code has already
                     ensured that the query will form a valid URL (all
                     reserved characters have been escaped). If true, this
                     method will escape the query and any URL parameters
                     provided.

    Returns:
      httplib.HTTPResponse The server's response to the GET request.
    """
    query_connection = self._CreateConnection(uri, 'GET', extra_headers,
        url_params, escape_params)

    return query_connection.getresponse()

  def Post(self, data, uri, extra_headers=None, url_params=None, 
           escape_params=True, content_type='application/atom+xml'):
    """Insert data into an APP server at the given URI.

    Args:
      data: string, ElementTree._Element, or something with a __str__ method 
            The XML to be sent to the uri. 
      uri: string The location (feed) to which the data should be inserted. 
           Example: '/base/feeds/items'. 
      extra_headers: dict (optional) HTTP headers which are to be included. 
                     The client automatically sets the Content-Type,
                     Authorization, and Content-Length headers.
      url_params: dict (optional) Additional URL parameters to be included
                  in the URI. These are translated into query arguments
                  in the form '&dict_key=value&...'.
                  Example: {'max-results': '250'} becomes &max-results=250
      escape_params: boolean (optional) If false, the calling code has already
                     ensured that the query will form a valid URL (all
                     reserved characters have been escaped). If true, this
                     method will escape the query and any URL parameters
                     provided.

    Returns:
      httplib.HTTPResponse Server's response to the POST request.
    """
    if isinstance(data, ElementTree._Element):
      data_str = ElementTree.tostring(data)
    else:
      data_str = str(data)
    
    extra_headers['Content-Length'] = len(data_str)
    extra_headers['Content-Type'] = content_type
    insert_connection = self._CreateConnection(uri, 'POST', extra_headers,
        url_params, escape_params)

    insert_connection.send(data_str)

    return insert_connection.getresponse()

  def Put(self, data, uri, extra_headers=None, url_params=None, 
           escape_params=True, content_type='application/atom+xml'):
    """Updates an entry at the given URI.
     
    Args:
      data: string, ElementTree._Element, or xml_wrapper.ElementWrapper The 
            XML containing the updated data.
      uri: string A URI indicating entry to which the update will be applied.
           Example: '/base/feeds/items/ITEM-ID'
      extra_headers: dict (optional) HTTP headers which are to be included.
                     The client automatically sets the Content-Type,
                     Authorization, and Content-Length headers.
      url_params: dict (optional) Additional URL parameters to be included
                  in the URI. These are translated into query arguments
                  in the form '&dict_key=value&...'.
                  Example: {'max-results': '250'} becomes &max-results=250
      escape_params: boolean (optional) If false, the calling code has already
                     ensured that the query will form a valid URL (all
                     reserved characters have been escaped). If true, this
                     method will escape the query and any URL parameters
                     provided.
  
    Returns:
      httplib.HTTPResponse Server's response to the PUT request.
    """
    if isinstance(data, ElementTree._Element):
      data_str = ElementTree.tostring(data)
    else:
      data_str = str(data)
      
    extra_headers['Content-Length'] = len(data_str)
    extra_headers['Content-Type'] = content_type
    update_connection = self._CreateConnection(uri, 'PUT', extra_headers,
        url_params, escape_params)

    update_connection.send(data_str)

    return update_connection.getresponse()

  def Delete(self, uri, extra_headers=None, url_params=None, 
             escape_params=True):
    """Deletes the entry at the given URI.

    Args:
      uri: string The URI of the entry to be deleted. Example: 
           '/base/feeds/items/ITEM-ID'
      extra_headers: dict (optional) HTTP headers which are to be included.
                     The client automatically sets the Content-Type and
                     Authorization headers.
      url_params: dict (optional) Additional URL parameters to be included
                  in the URI. These are translated into query arguments
                  in the form '&dict_key=value&...'.
                  Example: {'max-results': '250'} becomes &max-results=250
      escape_params: boolean (optional) If false, the calling code has already
                     ensured that the query will form a valid URL (all
                     reserved characters have been escaped). If true, this
                     method will escape the query and any URL parameters
                     provided.

    Returns:
      httplib.HTTPResponse Server's response to the DELETE request.
    """
    delete_connection = self._CreateConnection(uri, 'DELETE', extra_headers,
        url_params, escape_params)

    return delete_connection.getresponse()

def DictionaryToParamList(url_parameters, escape_params=True):
  """Convert a dictionary of URL arguments into a URL parameter string.

  Args:
    url_parameters: The dictionaty of key-value pairs which will be converted
                    into URL parameters. For example,
                    {'dry-run': 'true', 'foo': 'bar'}
                    will become ['dry-run=true', 'foo=bar'].

  Returns:
    A list which contains a string for each key-value pair. The strings are
    ready to be incorporated into a URL by using '&'.join([] + parameter_list)
  """
  # Choose which function to use when modifying the query and parameters.
  # Use quote_plus when escape_params is true.
  transform_op = [str, urllib.quote_plus][bool(escape_params)]
  # Create a list of tuples containing the escaped version of the
  # parameter-value pairs.
  parameter_tuples = [(transform_op(param), transform_op(value))
                     for param, value in (url_parameters or {}).items()]
  # Turn parameter-value tuples into a list of strings in the form
  # 'PARAMETER=VALUE'.

  return ['='.join(x) for x in parameter_tuples]


def BuildUri(uri, url_params=None, escape_params=True):
  """Converts a uri string and a collection of parameters into a URI.

  Args:
    uri: string
    url_params: dict (optional)
    escape_params: boolean (optional)
    uri: string The start of the desired URI. This string can alrady contain
         URL parameters. Examples: '/base/feeds/snippets', 
         '/base/feeds/snippets?bq=digital+camera'
    url_parameters: dict (optional) Additional URL parameters to be included
                    in the query. These are translated into query arguments
                    in the form '&dict_key=value&...'.
                    Example: {'max-results': '250'} becomes &max-results=250
    escape_params: boolean (optional) If false, the calling code has already
                   ensured that the query will form a valid URL (all
                   reserved characters have been escaped). If true, this
                   method will escape the query and any URL parameters
                   provided.

  Returns:
    string The URI consisting of the escaped URL parameters appended to the
    initial uri string.
  """
  # Prepare URL parameters for inclusion into the GET request.
  parameter_list = DictionaryToParamList(url_params, escape_params)

  # Append the URL parameters to the URL.
  if parameter_list:
    if uri.find('?') != -1:
      # If there are already URL parameters in the uri string, add the
      # parameters after a new & character.
      full_uri = '&'.join([uri] + parameter_list)
    else:
      # The uri string did not have any URL parameters (no ? character)
      # so put a ? between the uri and URL parameters.
      full_uri = '%s%s' % (uri, '?%s' % ('&'.join([] + parameter_list)))  
  else:
    full_uri = uri
        
  return full_uri
