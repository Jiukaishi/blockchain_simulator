挖矿
挖矿过程就是计算上述区块hash的过程，几乎所有的机器都可以挖矿成功。关键在于谁先挖到矿，因为当一台机器挖矿成功就向网络广播，其他挖矿在对这个hash进行校验之后，就停止自己的挖矿，开始基于这个区块挖新的矿。而每一个被挖到区块中记录的第一笔交易是给挖到这个区块的矿工自己的奖励金，所以抢到第一个挖矿成功名额对于矿工来说至关重要。

前面说过，计算区块hash过程里面，会以区块包含的交易的merkle hash root作为计算的一个参数，因此，挖矿时，矿工会事先从自己本地的交易信息里面提炼出merkle hash root，也就是说，在挖矿之前，对于当前这个矿工来说，新区块会包含哪些交易就已经确定好了的。关于这个过程，可以阅读《Merkle Tree》。


Register cluster instead of routing