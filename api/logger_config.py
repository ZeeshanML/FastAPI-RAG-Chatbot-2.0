import logging

def setup_logger():
    # Configure logging for AWS CloudWatch
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Create a custom formatter that includes file name and line number
    formatter = logging.Formatter(
        '[%(levelname)s]\t%(asctime)s.%(msecs)03dZ\t%(aws_request_id)s\t'
        '%(filename)s:%(lineno)d\t%(message)s',
        '%Y-%m-%dT%H:%M:%S'
    )

    class RequestContextFilter(logging.Filter):
        def filter(self, record):
            record.aws_request_id = getattr(record, 'aws_request_id', 'local')
            return True

    # Add handler if running in Lambda
    if len(logger.handlers) > 0:
        # AWS Lambda adds a handler by default
        logger.handlers[0].setFormatter(formatter)
    else:
        # Running locally
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    logger.addFilter(RequestContextFilter())
    return logger