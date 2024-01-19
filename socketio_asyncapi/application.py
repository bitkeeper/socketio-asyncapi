import inspect
import asyncio
from typing import Callable, Optional, Type, Union

from socketio import AsyncServer
from loguru import logger
from pydantic import BaseModel, ValidationError

from socketio_asyncapi.asyncapi.docs import AsyncAPIDoc, NotProvidedType


class BaseValildationError(ValidationError):
    @classmethod
    def init_from_super(cls, parent: ValidationError) -> "BaseValildationError":
        """Initialize EmitValidationError from parent ValidationError"""
        return cls(
            errors=parent.raw_errors,
            model=parent.model,
        )


class RequestValidationError(BaseValildationError):
    pass

# class ResponseValidationError(BaseValildationError):
#     pass

# class EmitValidationError(BaseValildationError):
#     pass

# TODO: merg into one exeception type to emit validation


class EmitValidationError(Exception):
    def __init__(self, message, event_name):
        super().__init__(message)
        self.event_name = event_name


class ResponseValidationError(Exception):
    def __init__(self, message, event_name):
        super().__init__(message)
        self.event_name = event_name


class AsyncAPISocketIO(AsyncServer):
    """Inherits the :class:`socketio.AsyncServer` class.
    Adds ability to validate with pydantic models and generate AsycnAPI spe.

    Example::
        socket = AsyncAPISocketIO(app, async_mode='threading', logger=True)
        class TokenModel(BaseModel):
            token: int

        class UserModel(BaseModel):
            name: str
            id: int

        @socket.on('get_user', response_model=UserModel)
        def get_user():
            return {"name": Bob, "id": 123}
    """

    def __init__(
        self,
        *args,
        validate: bool = False,
        generate_docs: bool = True,
        version: str = "1.0.0",
        title: str = "Demo Chat API",
        description: str = "Demo Chat API",
        server_url: str = "http://localhost:5000",
        server_name: str = "BACKEND",
        **kwargs,
    ):
        """Create AsycnAPISocketIO

        Args:
            app (Optional[Flask]): flask app
            validation (bool, optional): If True request and response will be validated. Defaults to True.
            generate_docs (bool, optional): If True AsyncAPI specs will be generated. Defaults to False.
            version (str, optional): AsyncAPI version. Defaults to "1.0.0".
            title (str, optional): AsyncAPI title. Defaults to "Demo Chat API".
            description (str, optional): AsyncAPI description. Defaults to "Demo Chat API".
            server_url (str, optional): AsyncAPI server url. Defaults to "http://localhost:5000".
            server_name (str, optional): AsyncAPI server name. Defaults to "BACKEND".
        """
        self.validate = validate
        self.generate_docs = generate_docs
        self.asyncapi_doc: AsyncAPIDoc = \
            AsyncAPIDoc.default_init(
                version=version,
                title=title,
                description=description,
                server_url=server_url,
                server_name=server_name,
            )
        super().__init__(*args, **kwargs)
        # self.emit_models: dict[str, Type[BaseModel]] = {}
        self.emit_models: dict[str, Optional[Type[Union[BaseModel,
                                                        int, str, bool, float, dict]]]] = {}

        self.exception_handlers: dict[str, Callable] = {}
        # TODO: set type to coroutine
        self.default_exception_handler: Optional[Callable] = None

    async def emit(self, event: str, *args, **kwargs):
        """
        Overrides emit in order to validate data with pydantic models

        for more info refer to :meth:`flask_socketio.SocketIO.emit`
        """
        if self.validate:
            model = self.emit_models.get(event)
            if model is not None:
                try:
                    if issubclass(model, BaseModel) and isinstance(args[0], model):
                        # args[0] = args[0].dict()
                        args = (args[0].dict(), *args[1:])
                    # elif issubclass(model, BaseModel) and isinstance(args[0], dict):
                    #     try:
                    #         model.validate(args[0])
                    #     except ValidationError as e:
                    #         logger.error(f"Error validating emit '{event}': {e}")
                    #         raise EmitValidationError.init_from_super(e)
                    elif not (isinstance(args[0], model)):
                        message = f"Error validating emit '{event}': data doesn't match the required datatype {model.__name__}"
                        logger.error(message)
                        raise EmitValidationError(message, event)
                except Exception as exc:
                    err_handler = self.default_exception_handler
                    if err_handler is None:
                        raise
                    return await err_handler(exc)

        return await super().emit(event, *args, **kwargs)

    def doc_emit(self, event: str, model: Optional[Type[Union[BaseModel, int, str, bool, float, dict]]], namespace=None, discription: str = ""):
        """
        Decorator to register/document a SocketIO emit event. This will be
        used to generate AsyncAPI specs and validate emits calls.

        Args:
            event (str): event name
            model (Type[BaseModel]): pydantic model
        """
        def decorator(func):
            if self.emit_models.get(event):
                if self.emit_models.get(event) != model:
                    raise ValueError(
                        f"Event {event} already registered with different model {model.__name__}")
            else:
                self.emit_models[event] = model
                self.asyncapi_doc.add_new_sender(
                    namespace, event, model, discription)
            return func
        return decorator

    def on(
            self,
            message,
            namespace=None,
            *,
            get_from_typehint: bool = True,
            response_model: Optional[Union[Type[BaseModel],
                                           NotProvidedType]] = None,
            request_model: Optional[Union[Type[BaseModel],
                                          NotProvidedType]] = None,
    ):
        """Decorator to register a SocketIO event handler with additional functionalities

        Args:
            message (str): refer to SocketIO.on(message)
            namespace (str, optional): refer to SocketIO.on(namespace). Defaults to None.
            get_from_typehint (bool, optional): Get request and response models from typehint.
                request_model and response_model take precedence over typehints if not None.
                Defaults to False.
            response_model (Optional[Type[BaseModel]], optional): Acknowledge model used
                for validation and documentation. Defaults to None.
            request_model (Optional[Type[BaseModel]], optional): Request payload model used
                for validation and documentation. Defaults to None.
        """
        def decorator(handler: Callable):

            nonlocal request_model
            nonlocal response_model
            if get_from_typehint:
                try:
                    first_arg_name = inspect.getfullargspec(handler)[0][-1]
                except IndexError:
                    posible_request_model = None
                else:
                    posible_request_model = handler.__annotations__.get(
                        first_arg_name, "NotProvided")
                posible_response_model = handler.__annotations__.get(
                    "return", "NotProvided")
                if request_model is None:
                    request_model = posible_request_model  # type: ignore
                if response_model is None:
                    response_model = posible_response_model  # type: ignore

            # print(f"request_model: {request_model}")
            # print(f"response_model: {response_model}")

            if self.generate_docs:
                self.asyncapi_doc.add_new_receiver(
                    handler,
                    namespace,
                    message,
                    ack_data_model=response_model,
                    payload_model=request_model,
                )

            async def wrapper(*args, **kwargs):
                new_handler = self._handle_all(
                    message,
                    request_model=request_model,
                    response_model=response_model
                )(handler)
                return await new_handler(*args, **kwargs)

            # Decorate with SocketIO.on decorator
            super(AsyncAPISocketIO, self).on(
                message, namespace=namespace)(wrapper)
            return wrapper
        return decorator

    def on_error_default(self, exception_handler: Callable):
        """Decorator to define a default error handler for SocketIO events.

        This decorator can be applied to a function that acts as a default
        error handler for any namespaces that do not have a specific handler.
        Example::

            @socketio.on_error_default
            def error_handler(e):
                print('An error has occurred: ' + str(e))
        """
        if not callable(exception_handler):
            raise ValueError('exception_handler must be callable')
        self.default_exception_handler = exception_handler
        return exception_handler

    # def on_error(self, namespace=None):
    #     """Decorator to define a custom error handler for SocketIO events.

    #     This decorator can be applied to a function that acts as an error
    #     handler for a namespace. This handler will be invoked when a SocketIO
    #     event handler raises an exception. The handler function must accept one
    #     argument, which is the exception raised. Example::

    #         @socketio.on_error(namespace='/chat')
    #         def chat_error_handler(e):
    #             print('An error has occurred: ' + str(e))

    #     :param namespace: The namespace for which to register the error
    #                       handler. Defaults to the global namespace.
    #     """
    #     namespace = namespace or '/'

    #     def decorator(exception_handler):
    #         if not callable(exception_handler):
    #             raise ValueError('exception_handler must be callable')
    #         self.exception_handlers[namespace] = exception_handler
    #         return exception_handler
    #     return decorator

    def _handle_all(self,
                    message: str,
                    response_model: Optional[Union[Type[BaseModel],
                                                   NotProvidedType]] = None,
                    request_model: Optional[Union[Type[BaseModel],
                                                  NotProvidedType]] = None,
                    ):
        """Decorator to validate request and response with pydantic models
        Args:
            handler (Callable, optional): handler function. Defaults to None.
            response_model (Optional[Type[BaseModel]], optional): Acknowledge model used
                for validation and documentation. Defaults to None.
            request_model (Optional[Type[BaseModel]], optional): Request payload model used
                for validation and documentation. Defaults to None.

        Raises: RequestValidationError, ResponseValidationError
        """

        def decorator(handler: Callable):

            async def wrapper(*args, **kwargs):
                did_request_came_as_arg = False
                request = None
                # check if request is in args or kwargs
                if len(args) > 1:
                    did_request_came_as_arg = True
                    request = args[-1]
                if not request:
                    did_request_came_as_arg = False
                    request = kwargs.get("request")

                # if there is a request in args or kwargs, validate it
                try:
                    if request and self.validate and request_model and request_model != NotProvidedType and request_model != 'NotProvided':
                        if issubclass(request_model, BaseModel):
                            try:
                                request_model.validate(request)  # type: ignore
                            except ValidationError as e:
                                logger.error(
                                    f"ValidationError for incoming request: {e}")
                                raise RequestValidationError.init_from_super(e)

                            request = request_model.parse_obj(
                                request)  # type: ignore
                        else:  # not a base model
                            try:
                                request = request_model(request)
                            except ValueError as exc:
                                logger.error(
                                    "ValidationError for incoming request")
                                raise RequestValidationError(
                                    errors=[], model=request_model)

                        if did_request_came_as_arg:
                            args = (args[0], request, *args[2:])
                        else:
                            kwargs["request"] = request

                    # call handler with converted request and validate response
                    if asyncio.iscoroutinefunction(handler):
                        response = await handler(*args, **kwargs)
                    else:
                        response = handler(*args, **kwargs)

                    if response:
                        if isinstance(response, response_model) is False:
                            # TODO: we require the event name in the handler for correct logging and exception handling
                            # event= message
                            reason = f"Error validating reponse '{message}': data doesn't match the required datatype {response_model.__name__}"
                            logger.error(reason)
                            raise ResponseValidationError(
                                message=reason, event_name=message)

                except Exception as exc:
                    # err_handler = self.exception_handlers.get(
                    #     namespace, self.default_exception_handler)
                    err_handler = self.default_exception_handler
                    if err_handler is None:
                        return
                        # raise
                    # _type, value, traceback = sys.exc_info()
                    if asyncio.iscoroutinefunction(handler):
                        response = await err_handler(exc)
                    else:
                        response = err_handler(exc)
                # if response is a pydantic model, convert it to json
                if isinstance(response, BaseModel):
                    return response.dict()
                else:
                    return response

            return wrapper
        return decorator
