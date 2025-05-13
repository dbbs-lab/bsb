class KernelWarning(Warning):
    pass


class NestError(Exception):
    pass


class NestKernelError(NestError):
    pass


class NestModuleError(NestKernelError):
    pass


class NestModelError(NestError):
    pass


class NestConnectError(NestError):
    pass
