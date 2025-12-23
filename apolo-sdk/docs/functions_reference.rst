==============
Initialization
==============


.. currentmodule:: apolo_sdk

.. _client-instantiation:

API functions
=============

.. function:: get( \
                    *, \
                    path: Optional[Path] = None, \
                    timeout: aiohttp.ClientTimeout = DEFAULT_TIMEOUT \
                ) -> AsyncContextManager[Client]
   :async:

   The handy API for getting initialized :class:`Client` instance.

   A shortcut for :meth:`Factory.get` that acts as asynchronous context manager.

   The usage is::

      async with apolo_sdk.get() as client:
          async with client.jobs.list() as jobs:
              async for job in jobs:
                  print(job.id)

   See :meth:`Factory.get` for optional function arguments meaning.


.. function:: login( \
                    show_browser_cb: Callable[[URL], Awaitable[None]], \
                    *, \
                    url: URL = DEFAULT_API_URL, \
                    path: Optional[Path] = None, \
                    timeout: aiohttp.ClientTimeout = DEFAULT_TIMEOUT \
                ) -> None
   :async:

   A shortcut for :meth:`Factory.login`. See the method for details.


.. function:: login_with_headless( \
                    get_auth_code_cb: Callable[[URL], Awaitable[str]], \
                    *, \
                    url: URL = DEFAULT_API_URL, \
                    path: Optional[Path] = None, \
                    timeout: aiohttp.ClientTimeout = DEFAULT_TIMEOUT \
                ) -> None
   :async:

   A shortcut for :meth:`Factory.login_headless`. See the method for details.

.. function:: login_with_token( \
                    token: str, \
                    *, \
                    url: URL = DEFAULT_API_URL, \
                    path: Optional[Path] = None, \
                    timeout: aiohttp.ClientTimeout = DEFAULT_TIMEOUT \
                ) -> None
   :async:

   A shortcut for :meth:`Factory.login_with_token`. See the method for details.

.. function:: logout(\
                    *, \
                    path: Optional[Path] = None, \
                    show_browser_cb: Callable[[URL], Awaitable[None]] = None, \
                ) -> None

   A shortcut for :meth:`Factory.logout`. See the method for details.


Config Factory
==============


.. class:: Factory(path: Optional[Path])

   A *factory* that used for making :class:`Client` instances, logging into Apolo
   Platform and logging out.

   *path* (:class:`pathlib.Path`) can be provided for pointing on a *custom*
   configuration directory (``~/.apolo`` by default). The default value can be overridden
   by ``APOLO_CONFIG`` environment variable.

   .. attribute:: path

      Revealed path to the configuration directory, expanded as described above.

      Read-only :class:`pathlib.Path` property.

      .. versionadded:: 20.2.25

   .. attribute:: is_config_present

      ``True`` if config files are present under :attr:`path`, ``False`` otherwise.

      Read-only :class:`bool` property.

   .. method:: get(*, timeout: aiohttp.ClientTimeout = DEFAULT_TIMEOUT) -> Client
      :async:

      Read configuration previously created by *login methods* and return a client
      instance. Update authorization token if needed.

      The easiest way to create required configuration file is running ``apolo login``
      :term:`CLI` command before the first call of this method from a user code.

      :param aiohttp.ClientTimeout timeout: optional timeout for HTTP operations, see
                                            also :ref:`timeouts`.

      :return: :class:`Client` that can be used for working with Apolo Platform.

      :raise: :exc:`ConfigError` if configuration file doesn't exist, malformed or not
              compatible with SDK version.

   .. method:: login( \
                     show_browser_cb: Callable[[URL], Awaitable[None]], \
                     *, \
                     url: URL = DEFAULT_API_URL, \
                     timeout: aiohttp.ClientTimeout = DEFAULT_TIMEOUT, \
                 ) -> None
      :async:

      Log into Apolo Platform using in-browser authorization method.

      The method is dedicated for login from workstation with GUI system. For
      logging in from server please use :meth:`login_headless`.

      The caller provides *show_browser_cb* callback which is called with URL argument.

      The callback should open a browser with this URL (:func:`webbrowser.open` can be
      used).

      After the call the configuration file is created, call :meth:`get` for
      making a client and performing Apolo Platform operations.

      :param show_browser_cb: a callback that should open a browser with specified URL
                              for handling authorization.

      :param ~yarl.URL url: Apolo Platform API URL,
                            ``URL("https://api.apolo.us/api/v1/")`` by default.

      :param aiohttp.ClientTimeout timeout: optional timeout for HTTP operations, see
                                            also :ref:`timeouts`.

   .. method:: login_headless( \
                      get_auth_code_cb: Callable[[URL], Awaitable[str]], \
                      *, \
                      url: URL = DEFAULT_API_URL, \
                      timeout: aiohttp.ClientTimeout = DEFAULT_TIMEOUT, \
                  ) -> None
      :async:

      Log into Apolo Platform using two-step authorization method.

      The method is dedicated for login from remote server that has no GUI system.
      For logging in from GUI equipped workstation please use :meth:`login`.

      The caller provides *get_auth_code_cb* callback which is called with URL argument.

      Usually, the callback prints given URL on screen and displays a prompt.

      User copies the URL from remote terminal session into local browser, authorizes
      and enters authorization code shown in the browser back into prompt.

      After the call the configuration file is created, call :meth:`get` for
      making a client and performing Apolo Platform operations.

      :param get_auth_code_cb: a callback that receives an URL and returns
                               authorization code.

      :param ~yarl.URL url: Apolo Platform API URL,
                            ``URL("https://api.apolo.us/api/v1/")`` by default.

      :param aiohttp.ClientTimeout timeout: optional timeout for HTTP operations, see
                                            also :ref:`timeouts`.

   .. method:: login_with_token( \
                      token: str, \
                      *, \
                      url: URL = DEFAULT_API_URL, \
                      timeout: aiohttp.ClientTimeout = DEFAULT_TIMEOUT, \
                  ) -> None
      :async:

      Log into Apolo Platform using previously acquired token.  The method is
      deprecated and not recommended to use.  Provided tokens will be revoked
      eventually.

      :param str token: authorization token.

      :param ~yarl.URL url: Apolo Platform API URL,
                            ``URL("https://api.apolo.us/api/v1/")`` by default.

      :param aiohttp.ClientTimeout timeout: optional timeout for HTTP operations, see
                                            also :ref:`timeouts`.

   .. method:: login_with_passed_config( \
                      config_data: Optional[str] = None, \
                      *, \
                      timeout: aiohttp.ClientTimeout = DEFAULT_TIMEOUT, \
                  ) -> None
      :async:

       Log into Apolo Platform using config data passed by platform. Use this only
       to login from the job that was started with ``pass_config=True``. Inside such
       job, `config_data` is available under ``APOLO_PASSED_CONFIG`` environment variable.

       :param str config_data: config data passed by platform.

       :param aiohttp.ClientTimeout timeout: optional timeout for HTTP operations, see
                                             also :ref:`timeouts`.

   .. method:: logout(show_browser_cb: Callable[[URL], Awaitable[None]] = None)
      :async:

      Log out from Apolo Platform. In case *show_browser_cb* callback passed,
      the browser will be opened to remove session cookie.

      :param show_browser_cb: a callback that should open a browser with specified URL
                              for handling authorization.

.. _timeouts:

Timeouts
========

By default the SDK raises :exc:`asyncio.TimeoutError` if the server doesn't respond in a
minute. It can be overridden by passing *timeout* argument to :class:`Factory` methods.
