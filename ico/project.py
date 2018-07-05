import ico
from populus import Project
from populus.config.chain import ChainConfig
from populus.wait import Wait


class IcoChainConfig(ChainConfig):
    timeout = 1000

    def get_chain(self, *args, **kwargs):
        class IcoChain(self.chain_class):
            @property
            def wait(self):
                return Wait(self.web3, timeout=IcoChainConfig.timeout)

        self.chain_class = IcoChain
        setattr(ico.project, 'IcoChain', IcoChain)
        return super(IcoChainConfig, self).get_chain(*args, **kwargs)


class IcoProject(Project):
    # FIXME: Temporary fix to increase timeout in populus
    # Remove this code once
    # https://github.com/ethereum/populus/pull/464 gets merged

    def __init__(self, *args, **kwargs):
        self.timeout = kwargs.pop('timeout', 1000)
        super(IcoProject, self).__init__(*args, **kwargs)

    def get_chain_config(self, chain_name):
        chain_config_key = 'chains.{chain_name}'.format(chain_name=chain_name)
        IcoChainConfig.timeout = self.timeout
        if chain_config_key in self.config:
            return self.config.get_config(chain_config_key, config_class=IcoChainConfig)
        else:
            raise KeyError(
                "Unknown chain: {0!r} - Must be one of {1!r}".format(
                    chain_name,
                    sorted(self.config.get('chains', {}).keys()),
                )
            )
