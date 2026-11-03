/* Trending Tokens' sample: one real ranking, captured from the BlockLens API
   on 2026-11-03 and frozen. Shown only when the API cannot be
   reached, under a "Sample data" badge naming the snapshot date: these
   prices are not live, and the screen says so. Holder counts are left out
   rather than shown stale. */
import type { TrendingResponse } from './api';

export const SAMPLE_TRENDING: TrendingResponse = {
 "provenance": "sample",
 "window": "h24",
 "asOf": "2026-11-03T12:20:55.946515+00:00",
 "stale": false,
 "pools": [
  {
   "rank": 1.0,
   "pool": "0x2df380544b88adb3ad0a94100dcc45fd705aae2d",
   "url": "https://dexscreener.com/base/0x2df380544b88adb3ad0a94100dcc45fd705aae2d",
   "dex": "Uniswap V3 (Base)",
   "token": "0x07b3d902783c3c12b077508c3b5c00113d1291d0",
   "name": "Doppler Finance",
   "symbol": "XDP",
   "quote": "USDC",
   "logo": "https://coin-images.coingecko.com/coins/images/102175227/large/03_Doppler_Symbol_Gradient_onDark_withBG.png?1785842913",
   "price": 0.01794,
   "change": {
    "m5": -0.02,
    "h1": -0.03,
    "h6": -0.98,
    "h24": -0.63
   },
   "volume": {
    "m5": 45614.84,
    "h1": 499091.82,
    "h6": 3351893.4,
    "h24": 18571483.37
   },
   "buys": {
    "m5": 88.0,
    "h1": 1065.0,
    "h6": 6767.0,
    "h24": 32579.0
   },
   "sells": {
    "m5": 99.0,
    "h1": 1060.0,
    "h6": 6843.0,
    "h24": 32591.0
   },
   "makers": {
    "m5": 70.0,
    "h1": 125.0,
    "h6": 652.0,
    "h24": 2571.0
   },
   "liquidity": 1746757.18,
   "marketCap": 17949406.0,
   "fdv": 179494057.0,
   "createdAt": 1790599925000.0,
   "holders": null
  },
  {
   "rank": 2.0,
   "pool": "0x6cdcb1c4a4d1c3c6d054b27ac5b77e89eafb971d",
   "url": "https://dexscreener.com/base/0x6cdcb1c4a4d1c3c6d054b27ac5b77e89eafb971d",
   "dex": "Aerodrome (Base)",
   "token": "0x940181a94a35a4569e4529a3cdfb74e38fd98631",
   "name": "Aerodrome",
   "symbol": "AERO",
   "quote": "USDC",
   "logo": "https://coin-images.coingecko.com/coins/images/31745/large/token.png?1696530564",
   "price": 0.6105,
   "change": {
    "m5": 0.82,
    "h1": 1.2,
    "h6": 1.83,
    "h24": -1.73
   },
   "volume": {
    "m5": 13272.9,
    "h1": 18347.33,
    "h6": 82359.68,
    "h24": 423378.2
   },
   "buys": {
    "m5": 16.0,
    "h1": 49.0,
    "h6": 187.0,
    "h24": 472.0
   },
   "sells": {
    "m5": 5.0,
    "h1": 5.0,
    "h6": 44.0,
    "h24": 706.0
   },
   "makers": {
    "m5": 23.0,
    "h1": 30.0,
    "h6": 142.0,
    "h24": 438.0
   },
   "liquidity": 5333918.18,
   "marketCap": 476013567.0,
   "fdv": 1225447366.0,
   "createdAt": 1694127055000.0,
   "holders": null
  },
  {
   "rank": 3.0,
   "pool": "0x5116773e18a9c7bb03ebb961b38678e45e238923",
   "url": "https://dexscreener.com/base/0x5116773e18a9c7bb03ebb961b38678e45e238923",
   "dex": "Uniswap V3 (Base)",
   "token": "0x3ec2156d4c0a9cbdab4a016633b7bcf6a8d68ea2",
   "name": "DebtReliefBot",
   "symbol": "DRB",
   "quote": "WETH",
   "logo": "https://coin-images.coingecko.com/coins/images/54784/large/1000143570.jpg?1759054009",
   "price": 9.854e-05,
   "change": {
    "m5": -0.02,
    "h1": 0.24,
    "h6": 1.58,
    "h24": -8.85
   },
   "volume": {
    "m5": 141.85,
    "h1": 4984.26,
    "h6": 6482.97,
    "h24": 84248.31
   },
   "buys": {
    "m5": 0.0,
    "h1": 18.0,
    "h6": 33.0,
    "h24": 369.0
   },
   "sells": {
    "m5": 3.0,
    "h1": 18.0,
    "h6": 47.0,
    "h24": 565.0
   },
   "makers": {
    "m5": 3.0,
    "h1": 16.0,
    "h6": 39.0,
    "h24": 444.0
   },
   "liquidity": 1016091.24,
   "marketCap": 9724570.0,
   "fdv": 9724570.0,
   "createdAt": 1741341537000.0,
   "holders": null
  },
  {
   "rank": 4.0,
   "pool": "0x8e859b6cf564c4ac2b848693c85c496e81dbf6c8",
   "url": "https://dexscreener.com/base/0x8e859b6cf564c4ac2b848693c85c496e81dbf6c8",
   "dex": "Aero Slipstream (Base)",
   "token": "0x44b63af715d5ef02cc3646a6ce96875e11d69e85",
   "name": "Cambria",
   "symbol": "RSGP",
   "quote": "USDC",
   "logo": "https://coin-images.coingecko.com/coins/images/102172274/large/cambria-logo.png?1793295821",
   "price": 0.001386,
   "change": {
    "m5": 0.0,
    "h1": -0.02,
    "h6": -0.03,
    "h24": -7.13
   },
   "volume": {
    "m5": 7.09,
    "h1": 2195.01,
    "h6": 13078.18,
    "h24": 136136.96
   },
   "buys": {
    "m5": 0.0,
    "h1": 1.0,
    "h6": 28.0,
    "h24": 295.0
   },
   "sells": {
    "m5": 2.0,
    "h1": 17.0,
    "h6": 90.0,
    "h24": 526.0
   },
   "makers": {
    "m5": 3.0,
    "h1": 17.0,
    "h6": 103.0,
    "h24": 444.0
   },
   "liquidity": 312950.31,
   "marketCap": 1892376.0,
   "fdv": 6934781.0,
   "createdAt": 1793148100000.0,
   "holders": null
  },
  {
   "rank": 5.0,
   "pool": "0xc19d91d99afc0332e5013a569c9721cd9ecb51a14c851f7a189a140950a627fa",
   "url": "https://dexscreener.com/base/0xc19d91d99afc0332e5013a569c9721cd9ecb51a14c851f7a189a140950a627fa",
   "dex": "Uniswap V4 (Base)",
   "token": "0x5be75e3b0aff5d1a042a5363ae36acb1d6d755ea",
   "name": "Axis Token",
   "symbol": "AXIS",
   "quote": "USDC",
   "logo": "https://coin-images.coingecko.com/coins/images/102178869/large/axisrobotics.png?1790578974",
   "price": 0.1375,
   "change": {
    "m5": -0.06,
    "h1": 2.11,
    "h6": 3.96,
    "h24": 10.82
   },
   "volume": {
    "m5": 7594.6,
    "h1": 166108.58,
    "h6": 815019.57,
    "h24": 2744215.37
   },
   "buys": {
    "m5": 61.0,
    "h1": 1408.0,
    "h6": 6690.0,
    "h24": 18506.0
   },
   "sells": {
    "m5": 71.0,
    "h1": 1456.0,
    "h6": 6566.0,
    "h24": 18598.0
   },
   "makers": {
    "m5": 66.0,
    "h1": 548.0,
    "h6": 1338.0,
    "h24": 3687.0
   },
   "liquidity": 2435432.65,
   "marketCap": 22702162.0,
   "fdv": 137588858.0,
   "createdAt": 1792390745000.0,
   "holders": null
  },
  {
   "rank": 6.0,
   "pool": "0xd9edc75a3a797ec92ca370f19051babebfb2edee",
   "url": "https://dexscreener.com/base/0xd9edc75a3a797ec92ca370f19051babebfb2edee",
   "dex": "Aerodrome (Base)",
   "token": "0xc0634090f2fe6c6d75e61be2b949464abb498973",
   "name": "Keeta",
   "symbol": "KTA",
   "quote": "WETH",
   "logo": "https://coin-images.coingecko.com/coins/images/54723/large/2025-03-05_22.53.06.jpg?1741234207",
   "price": 0.05708,
   "change": {
    "m5": 0.3,
    "h1": -0.45,
    "h6": 0.41,
    "h24": -4.08
   },
   "volume": {
    "m5": 210.39,
    "h1": 10195.98,
    "h6": 32475.1,
    "h24": 130315.59
   },
   "buys": {
    "m5": 2.0,
    "h1": 25.0,
    "h6": 64.0,
    "h24": 212.0
   },
   "sells": {
    "m5": 0.0,
    "h1": 5.0,
    "h6": 59.0,
    "h24": 223.0
   },
   "makers": {
    "m5": 1.0,
    "h1": 14.0,
    "h6": 57.0,
    "h24": 132.0
   },
   "liquidity": 3484236.23,
   "marketCap": 35903794.0,
   "fdv": 57084267.0,
   "createdAt": 1741199569000.0,
   "holders": null
  },
  {
   "rank": 7.0,
   "pool": "0x01784ef301d79e4b2df3a21ad9a536d4cf09a5ce",
   "url": "https://dexscreener.com/base/0x01784ef301d79e4b2df3a21ad9a536d4cf09a5ce",
   "dex": "Aerodrome (Base)",
   "token": "0xacfe6019ed1a7dc6f7b508c02d1b04ec88cc21bf",
   "name": "Venice Token",
   "symbol": "VVV",
   "quote": "WETH",
   "logo": "https://coin-images.coingecko.com/coins/images/54023/large/VVV_Token_Transparent.png?1741856877",
   "price": 21.85,
   "change": {
    "m5": 0.4,
    "h1": 3.02,
    "h6": 2.02,
    "h24": -2.14
   },
   "volume": {
    "m5": 6723.74,
    "h1": 63655.42,
    "h6": 306393.04,
    "h24": 623224.57
   },
   "buys": {
    "m5": 26.0,
    "h1": 295.0,
    "h6": 1468.0,
    "h24": 6902.0
   },
   "sells": {
    "m5": 3.0,
    "h1": 14.0,
    "h6": 341.0,
    "h24": 759.0
   },
   "makers": {
    "m5": 19.0,
    "h1": 85.0,
    "h6": 380.0,
    "h24": 634.0
   },
   "liquidity": 7653753.74,
   "marketCap": 1071938032.0,
   "fdv": 1774712776.0,
   "createdAt": 1737996299000.0,
   "holders": null
  },
  {
   "rank": 8.0,
   "pool": "0x0c3b466104545efa096b8f944c1e524e1d0d4888",
   "url": "https://dexscreener.com/base/0x0c3b466104545efa096b8f944c1e524e1d0d4888",
   "dex": "Uniswap V2 (Base)",
   "token": "0xa4a2e2ca3fbfe21aed83471d28b6f65a233c6e00",
   "name": "Ribbita",
   "symbol": "TIBBIR",
   "quote": "VIRTUAL",
   "logo": "https://coin-images.coingecko.com/coins/images/54970/large/Untitled_design.png?1742941268",
   "price": 0.1992,
   "change": {
    "m5": 0.0,
    "h1": -0.18,
    "h6": 3.41,
    "h24": -1.0
   },
   "volume": {
    "m5": 0.0,
    "h1": 1551.89,
    "h6": 17439.9,
    "h24": 63973.41
   },
   "buys": {
    "m5": 0.0,
    "h1": 4.0,
    "h6": 47.0,
    "h24": 143.0
   },
   "sells": {
    "m5": 0.0,
    "h1": 20.0,
    "h6": 65.0,
    "h24": 151.0
   },
   "makers": {
    "m5": 0.0,
    "h1": 17.0,
    "h6": 49.0,
    "h24": 107.0
   },
   "liquidity": 2805486.24,
   "marketCap": 87705795.0,
   "fdv": 87705795.0,
   "createdAt": 1736641803000.0,
   "holders": null
  },
  {
   "rank": 9.0,
   "pool": "0x2836e062a3fe75943a7f4a552e2365b98e414e75",
   "url": "https://dexscreener.com/base/0x2836e062a3fe75943a7f4a552e2365b98e414e75",
   "dex": "Aero Slipstream (Base)",
   "token": "0xb200000000000000000000397293cb8cda9a10c5",
   "name": "Sandisk Corporation",
   "symbol": "SNDKC",
   "quote": "USDC",
   "logo": "https://coin-images.coingecko.com/coins/images/102178283/large/sndk-200.png?1789234014",
   "price": 1116.52,
   "change": {
    "m5": 0.42,
    "h1": 0.96,
    "h6": 3.65,
    "h24": -5.18
   },
   "volume": {
    "m5": 43473.56,
    "h1": 873012.81,
    "h6": 5452593.26,
    "h24": 19550850.31
   },
   "buys": {
    "m5": 40.0,
    "h1": 402.0,
    "h6": 2128.0,
    "h24": 9589.0
   },
   "sells": {
    "m5": 10.0,
    "h1": 314.0,
    "h6": 1869.0,
    "h24": 10192.0
   },
   "makers": {
    "m5": 30.0,
    "h1": 305.0,
    "h6": 524.0,
    "h24": 1046.0
   },
   "liquidity": 1036182.33,
   "marketCap": 1550081.0,
   "fdv": 1550081.0,
   "createdAt": 1792637453000.0,
   "holders": null
  },
  {
   "rank": 10.0,
   "pool": "0xde9ba4084bf0733a9d69e42e71e5fd140179df71",
   "url": "https://dexscreener.com/base/0xde9ba4084bf0733a9d69e42e71e5fd140179df71",
   "dex": "Uniswap V3 (Base)",
   "token": "0xe6522a891702cd2e8cc2a5182638c9da1dd44b22",
   "name": "Wrapped L1coin",
   "symbol": "WL1",
   "quote": "USDC",
   "logo": "https://coin-images.coingecko.com/coins/images/102174808/large/genesisl1-official-logo-200.png?1785000513",
   "price": 0.2955,
   "change": {
    "m5": -0.6,
    "h1": -6.39,
    "h6": -6.43,
    "h24": 21.34
   },
   "volume": {
    "m5": 5238.34,
    "h1": 25384.76,
    "h6": 39585.25,
    "h24": 194463.96
   },
   "buys": {
    "m5": 3.0,
    "h1": 17.0,
    "h6": 45.0,
    "h24": 226.0
   },
   "sells": {
    "m5": 3.0,
    "h1": 20.0,
    "h6": 35.0,
    "h24": 131.0
   },
   "makers": {
    "m5": 4.0,
    "h1": 22.0,
    "h6": 50.0,
    "h24": 190.0
   },
   "liquidity": 399801.44,
   "marketCap": 12535036.0,
   "fdv": 1096117.0,
   "createdAt": 1783628159000.0,
   "holders": null
  },
  {
   "rank": 11.0,
   "pool": "0xafe30319a948f322585fafc1cab1671a47eb3786",
   "url": "https://dexscreener.com/base/0xafe30319a948f322585fafc1cab1671a47eb3786",
   "dex": "Uniswap V3 (Base)",
   "token": "0x3e12b9d6a4d12cd9b4a6d613872d0eb32f68b380",
   "name": "Flower",
   "symbol": "FLOWER",
   "quote": "USDC",
   "logo": "https://coin-images.coingecko.com/coins/images/55689/large/flower_200.png?1747034605",
   "price": 0.1499,
   "change": {
    "m5": 0.07,
    "h1": -0.61,
    "h6": -2.16,
    "h24": -0.52
   },
   "volume": {
    "m5": 127.43,
    "h1": 767.39,
    "h6": 5163.06,
    "h24": 35357.64
   },
   "buys": {
    "m5": 1.0,
    "h1": 5.0,
    "h6": 34.0,
    "h24": 232.0
   },
   "sells": {
    "m5": 2.0,
    "h1": 13.0,
    "h6": 59.0,
    "h24": 290.0
   },
   "makers": {
    "m5": 2.0,
    "h1": 13.0,
    "h6": 71.0,
    "h24": 340.0
   },
   "liquidity": 224999.84,
   "marketCap": 3214337.0,
   "fdv": 3214337.0,
   "createdAt": 1746673785000.0,
   "holders": null
  },
  {
   "rank": 12.0,
   "pool": "0x995985c9027e8a90c823a5e0a9112fea72d1f4dd",
   "url": "https://dexscreener.com/base/0x995985c9027e8a90c823a5e0a9112fea72d1f4dd",
   "dex": "Aerodrome (Base)",
   "token": "0xef5997c2cf2f6c138196f8a6203afc335206b3c1",
   "name": "OWB",
   "symbol": "OWB",
   "quote": "USDC",
   "logo": "https://coin-images.coingecko.com/coins/images/70956/large/owb.png?1764799678",
   "price": 0.007583,
   "change": {
    "m5": 0.0,
    "h1": -1.09,
    "h6": 5.09,
    "h24": 3.57
   },
   "volume": {
    "m5": 0.0,
    "h1": 152.19,
    "h6": 4060.72,
    "h24": 13180.71
   },
   "buys": {
    "m5": 0.0,
    "h1": 0.0,
    "h6": 24.0,
    "h24": 88.0
   },
   "sells": {
    "m5": 0.0,
    "h1": 1.0,
    "h6": 21.0,
    "h24": 88.0
   },
   "makers": {
    "m5": 0.0,
    "h1": 1.0,
    "h6": 31.0,
    "h24": 102.0
   },
   "liquidity": 55498.44,
   "marketCap": 2829852.0,
   "fdv": 7583265.0,
   "createdAt": 1759747591000.0,
   "holders": null
  },
  {
   "rank": 13.0,
   "pool": "0x7a33000372f3f028f074182ccb9d16cbeefbf920",
   "url": "https://dexscreener.com/base/0x7a33000372f3f028f074182ccb9d16cbeefbf920",
   "dex": "Aero Slipstream (Base)",
   "token": "0xb2000000000000000000001e800a7f5189430cd0",
   "name": "Tesla Inc.",
   "symbol": "TSLAC",
   "quote": "USDC",
   "logo": "https://coin-images.coingecko.com/coins/images/102178285/large/tsla-200.png?1789234081",
   "price": 402.59,
   "change": {
    "m5": 0.07,
    "h1": 0.01,
    "h6": 0.35,
    "h24": -0.23
   },
   "volume": {
    "m5": 40016.21,
    "h1": 360239.08,
    "h6": 2342749.65,
    "h24": 7436659.96
   },
   "buys": {
    "m5": 19.0,
    "h1": 202.0,
    "h6": 926.0,
    "h24": 3388.0
   },
   "sells": {
    "m5": 23.0,
    "h1": 171.0,
    "h6": 893.0,
    "h24": 3663.0
   },
   "makers": {
    "m5": 35.0,
    "h1": 223.0,
    "h6": 538.0,
    "h24": 1018.0
   },
   "liquidity": 455118.99,
   "marketCap": 2185849.0,
   "fdv": 2185849.0,
   "createdAt": 1792637453000.0,
   "holders": null
  },
  {
   "rank": 14.0,
   "pool": "0x9331f571f79d1e186a095c93756b5680a43932ac",
   "url": "https://dexscreener.com/base/0x9331f571f79d1e186a095c93756b5680a43932ac",
   "dex": "Uniswap V3 (Base)",
   "token": "0xe0cd4cacddcbf4f36e845407ce53e87717b6601d",
   "name": "Impossible Cloud Network Token",
   "symbol": "ICNT",
   "quote": "USDC",
   "logo": "https://coin-images.coingecko.com/coins/images/55484/large/ICNT_token_%281%29_%281%29.png?1751614146",
   "price": 0.2292,
   "change": {
    "m5": 0.06,
    "h1": 7.24,
    "h6": 16.88,
    "h24": 38.58
   },
   "volume": {
    "m5": 4441.38,
    "h1": 62447.52,
    "h6": 238414.03,
    "h24": 523596.86
   },
   "buys": {
    "m5": 43.0,
    "h1": 583.0,
    "h6": 2308.0,
    "h24": 4947.0
   },
   "sells": {
    "m5": 34.0,
    "h1": 534.0,
    "h6": 2210.0,
    "h24": 4986.0
   },
   "makers": {
    "m5": 28.0,
    "h1": 155.0,
    "h6": 407.0,
    "h24": 736.0
   },
   "liquidity": 103779.52,
   "marketCap": 57993564.0,
   "fdv": 155603403.0,
   "createdAt": 1751473135000.0,
   "holders": null
  },
  {
   "rank": 15.0,
   "pool": "0xaec085e5a5ce8d96a7bdd3eb3a62445d4f6ce703",
   "url": "https://dexscreener.com/base/0xaec085e5a5ce8d96a7bdd3eb3a62445d4f6ce703",
   "dex": "Uniswap V3 (Base)",
   "token": "0x22af33fe49fd1fa80c7149773dde5890d3c76f3b",
   "name": "BankrCoin",
   "symbol": "BNKR",
   "quote": "WETH",
   "logo": "https://coin-images.coingecko.com/coins/images/52626/large/bankr-static.png?1736405365",
   "price": 0.0002645,
   "change": {
    "m5": 0.1,
    "h1": -0.23,
    "h6": 0.89,
    "h24": -1.53
   },
   "volume": {
    "m5": 26.29,
    "h1": 28.34,
    "h6": 1161.42,
    "h24": 25441.5
   },
   "buys": {
    "m5": 0.0,
    "h1": 2.0,
    "h6": 15.0,
    "h24": 227.0
   },
   "sells": {
    "m5": 1.0,
    "h1": 10.0,
    "h6": 46.0,
    "h24": 369.0
   },
   "makers": {
    "m5": 1.0,
    "h1": 3.0,
    "h6": 16.0,
    "h24": 173.0
   },
   "liquidity": 1664821.36,
   "marketCap": 25538243.0,
   "fdv": 25538243.0,
   "createdAt": 1733201093000.0,
   "holders": null
  },
  {
   "rank": 16.0,
   "pool": "0x5e3c5083f27654fac92126cb3fbd8773306cd90d",
   "url": "https://dexscreener.com/base/0x5e3c5083f27654fac92126cb3fbd8773306cd90d",
   "dex": "Aero Slipstream (Base)",
   "token": "0x2ae3f1ec7f1f5012cfeab0185bfc7aa3cf0dec22",
   "name": "Coinbase Wrapped Staked ETH",
   "symbol": "CBETH",
   "quote": "CBBTC",
   "logo": "https://coin-images.coingecko.com/coins/images/27008/large/cbeth.png?1709186989",
   "price": 2586.79,
   "change": {
    "m5": 0.02,
    "h1": -0.19,
    "h6": 1.13,
    "h24": -1.12
   },
   "volume": {
    "m5": 2434.18,
    "h1": 34688.18,
    "h6": 281620.93,
    "h24": 1608490.21
   },
   "buys": {
    "m5": 2.0,
    "h1": 16.0,
    "h6": 174.0,
    "h24": 996.0
   },
   "sells": {
    "m5": 0.0,
    "h1": 26.0,
    "h6": 161.0,
    "h24": 852.0
   },
   "makers": {
    "m5": 2.0,
    "h1": 34.0,
    "h6": 195.0,
    "h24": 575.0
   },
   "liquidity": 869974.36,
   "marketCap": 439855382.0,
   "fdv": 233055916.0,
   "createdAt": 1792637517000.0,
   "holders": null
  },
  {
   "rank": 17.0,
   "pool": "0x66dcd42e6314b287110922ae36cb2a8bdeecc153",
   "url": "https://dexscreener.com/base/0x66dcd42e6314b287110922ae36cb2a8bdeecc153",
   "dex": "Aero Slipstream (Base)",
   "token": "0xb2000000000000000000004884b426556b92883d",
   "name": "Strategy Inc.",
   "symbol": "MSTRC",
   "quote": "USDC",
   "logo": "https://coin-images.coingecko.com/coins/images/102178282/large/mstr-200.png?1789233935",
   "price": 131.4,
   "change": {
    "m5": 0.1,
    "h1": 0.05,
    "h6": 1.62,
    "h24": -1.34
   },
   "volume": {
    "m5": 82360.0,
    "h1": 699146.68,
    "h6": 4145899.81,
    "h24": 19674629.63
   },
   "buys": {
    "m5": 33.0,
    "h1": 277.0,
    "h6": 1783.0,
    "h24": 7724.0
   },
   "sells": {
    "m5": 36.0,
    "h1": 288.0,
    "h6": 1584.0,
    "h24": 7959.0
   },
   "makers": {
    "m5": 45.0,
    "h1": 286.0,
    "h6": 531.0,
    "h24": 1088.0
   },
   "liquidity": 987647.15,
   "marketCap": 1976634.0,
   "fdv": 1976634.0,
   "createdAt": 1792637429000.0,
   "holders": null
  },
  {
   "rank": 18.0,
   "pool": "0x6cf637a82362d304dfa56a6387fc8f909ec0008ec520ee5fb999506d9b1f3514",
   "url": "https://dexscreener.com/base/0x6cf637a82362d304dfa56a6387fc8f909ec0008ec520ee5fb999506d9b1f3514",
   "dex": "o1 Launchpad",
   "token": "0xb200000000000000000000585fd80c20af698f01",
   "name": "one life, its worth an attempt",
   "symbol": "WORTH",
   "quote": "ETH",
   "logo": "https://coin-images.coingecko.com/coins/images/102179793/large/worth.jpg?1793088281",
   "price": 0.0004845,
   "change": {
    "m5": 0.37,
    "h1": -4.91,
    "h6": -9.73,
    "h24": -36.26
   },
   "volume": {
    "m5": 74.63,
    "h1": 7354.84,
    "h6": 23970.49,
    "h24": 206428.33
   },
   "buys": {
    "m5": 1.0,
    "h1": 39.0,
    "h6": 89.0,
    "h24": 716.0
   },
   "sells": {
    "m5": 0.0,
    "h1": 12.0,
    "h6": 59.0,
    "h24": 517.0
   },
   "makers": {
    "m5": 1.0,
    "h1": 48.0,
    "h6": 95.0,
    "h24": 360.0
   },
   "liquidity": 94107.01,
   "marketCap": 484507.0,
   "fdv": 484507.0,
   "createdAt": 1786821111000.0,
   "holders": null
  },
  {
   "rank": 19.0,
   "pool": "0x7c84276e317f128b55bd270dbfba3ef94c84b984c124a1de7c4f72da90bfba45",
   "url": "https://dexscreener.com/base/0x7c84276e317f128b55bd270dbfba3ef94c84b984c124a1de7c4f72da90bfba45",
   "dex": "Uniswap V4 (Base)",
   "token": "0xed664536023d8e4b1640c394777d34abaff1df8f",
   "name": "Dolphin",
   "symbol": "POD",
   "quote": "ETH",
   "logo": "https://coin-images.coingecko.com/coins/images/70187/large/1_to_1_Dolphin_imresizer.jpg?1760947185",
   "price": 0.5298,
   "change": {
    "m5": 0.1,
    "h1": -2.54,
    "h6": -0.01,
    "h24": -0.28
   },
   "volume": {
    "m5": 1734.38,
    "h1": 37469.31,
    "h6": 106279.73,
    "h24": 660804.41
   },
   "buys": {
    "m5": 0.0,
    "h1": 4.0,
    "h6": 68.0,
    "h24": 380.0
   },
   "sells": {
    "m5": 3.0,
    "h1": 23.0,
    "h6": 65.0,
    "h24": 449.0
   },
   "makers": {
    "m5": 3.0,
    "h1": 18.0,
    "h6": 48.0,
    "h24": 188.0
   },
   "liquidity": 4296739.48,
   "marketCap": 44435829.0,
   "fdv": 264934305.0,
   "createdAt": 1772474055000.0,
   "holders": null
  },
  {
   "rank": 20.0,
   "pool": "0xa0473ced0cd1bfb857e3e04b5fa4b6af18c5e44d",
   "url": "https://dexscreener.com/base/0xa0473ced0cd1bfb857e3e04b5fa4b6af18c5e44d",
   "dex": "Aero Slipstream (Base)",
   "token": "0xb2000000000000000000007d16372840df4dabbe",
   "name": "Palantir Technologies Inc.",
   "symbol": "PLTRC",
   "quote": "USDC",
   "logo": "https://coin-images.coingecko.com/coins/images/102178880/large/PLTR.png?1790582134",
   "price": 165.016,
   "change": {
    "m5": 0.37,
    "h1": -0.13,
    "h6": -4.06,
    "h24": -11.37
   },
   "volume": {
    "m5": 14828.3,
    "h1": 170066.12,
    "h6": 617066.74,
    "h24": 3104089.09
   },
   "buys": {
    "m5": 28.0,
    "h1": 258.0,
    "h6": 816.0,
    "h24": 3580.0
   },
   "sells": {
    "m5": 23.0,
    "h1": 245.0,
    "h6": 841.0,
    "h24": 4171.0
   },
   "makers": {
    "m5": 37.0,
    "h1": 151.0,
    "h6": 297.0,
    "h24": 606.0
   },
   "liquidity": 370537.19,
   "marketCap": 398501.0,
   "fdv": 398501.0,
   "createdAt": 1792637661000.0,
   "holders": null
  },
  {
   "rank": 21.0,
   "pool": "0xff8104251e7761163fac3211ef5583fb3f8583d6",
   "url": "https://dexscreener.com/base/0xff8104251e7761163fac3211ef5583fb3f8583d6",
   "dex": "Baseline (Base)",
   "token": "0xff8104251e7761163fac3211ef5583fb3f8583d6",
   "name": "REPPO",
   "symbol": "REPPO",
   "quote": "VIRTUAL",
   "logo": "https://coin-images.coingecko.com/coins/images/70797/large/h-rOp1hB_400x400_%281%29.jpg?1763879875",
   "price": 0.00717095624705139,
   "change": {
    "m5": -0.017,
    "h1": 0.094,
    "h6": -3.332,
    "h24": -9.503
   },
   "volume": {
    "m5": 19.7137513491,
    "h1": 99.5152678844,
    "h6": 7830.4908392752,
    "h24": 55347.1441864843
   },
   "buys": {
    "m5": 0.0,
    "h1": 0.0,
    "h6": 84.0,
    "h24": 358.0
   },
   "sells": {
    "m5": 2.0,
    "h1": 5.0,
    "h6": 73.0,
    "h24": 222.0
   },
   "makers": {
    "m5": 1.0,
    "h1": 1.0,
    "h6": 9.0,
    "h24": 13.0
   },
   "liquidity": 448471.9866,
   "marketCap": 3120997.52752174,
   "fdv": 7133659.16275615,
   "createdAt": 1779981399000.0,
   "holders": null
  },
  {
   "rank": 22.0,
   "pool": "0x83f3aca29bc79b048b99c56013475570acc97ccf",
   "url": "https://dexscreener.com/base/0x83f3aca29bc79b048b99c56013475570acc97ccf",
   "dex": "Pancakeswap V3 (Base)",
   "token": "0x29cc30f9d113b356ce408667aa6433589cecbdca",
   "name": "Elsa",
   "symbol": "ELSA",
   "quote": "USDC",
   "logo": "https://coin-images.coingecko.com/coins/images/71623/large/Red_circle_white_logo_512x512_%281%29.png?1768570174",
   "price": 0.06437,
   "change": {
    "m5": -0.13,
    "h1": -0.14,
    "h6": -1.51,
    "h24": 2.33
   },
   "volume": {
    "m5": 3093.96,
    "h1": 15265.26,
    "h6": 116806.68,
    "h24": 852411.12
   },
   "buys": {
    "m5": 18.0,
    "h1": 107.0,
    "h6": 808.0,
    "h24": 4914.0
   },
   "sells": {
    "m5": 25.0,
    "h1": 131.0,
    "h6": 837.0,
    "h24": 5238.0
   },
   "makers": {
    "m5": 20.0,
    "h1": 51.0,
    "h6": 136.0,
    "h24": 294.0
   },
   "liquidity": 447244.43,
   "marketCap": 14741362.0,
   "fdv": 64378383.0,
   "createdAt": 1768899599000.0,
   "holders": null
  },
  {
   "rank": 23.0,
   "pool": "0x215b2146c3164aba3f5b18e8619b737c7f7dd11e5ba693646dcd9a336c5a30ba",
   "url": "https://dexscreener.com/base/0x215b2146c3164aba3f5b18e8619b737c7f7dd11e5ba693646dcd9a336c5a30ba",
   "dex": "o1 Launchpad",
   "token": "0xb2000000000000000000004c27f6523082f41d01",
   "name": "Basecat",
   "symbol": "BASECAT",
   "quote": "ETH",
   "logo": "https://coin-images.coingecko.com/coins/images/102175780/large/zi54rndmdx59nblfgry3d1pyckch.?1787558766",
   "price": 0.008337,
   "change": {
    "m5": 0.0,
    "h1": 0.49,
    "h6": -3.51,
    "h24": -12.15
   },
   "volume": {
    "m5": 0.0,
    "h1": 1419.63,
    "h6": 44923.98,
    "h24": 127206.57
   },
   "buys": {
    "m5": 0.0,
    "h1": 3.0,
    "h6": 104.0,
    "h24": 267.0
   },
   "sells": {
    "m5": 0.0,
    "h1": 6.0,
    "h6": 32.0,
    "h24": 95.0
   },
   "makers": {
    "m5": 0.0,
    "h1": 8.0,
    "h6": 95.0,
    "h24": 205.0
   },
   "liquidity": 406229.53,
   "marketCap": 8337782.0,
   "fdv": 8337782.0,
   "createdAt": 1786817029000.0,
   "holders": null
  },
  {
   "rank": 24.0,
   "pool": "0x868eed6bad4bd368cd053b766f84cc727697589a",
   "url": "https://dexscreener.com/base/0x868eed6bad4bd368cd053b766f84cc727697589a",
   "dex": "Aero Slipstream (Base)",
   "token": "0x311935cd80b76769bf2ecc9d8ab7635b2139cf82",
   "name": "Solana",
   "symbol": "SOL",
   "quote": "USDC",
   "logo": "https://coin-images.coingecko.com/coins/images/71099/large/solana.jpg?1765793164",
   "price": 92.88,
   "change": {
    "m5": 0.2,
    "h1": 0.55,
    "h6": 1.66,
    "h24": -1.62
   },
   "volume": {
    "m5": 78813.33,
    "h1": 231771.79,
    "h6": 1438352.82,
    "h24": 5814536.9
   },
   "buys": {
    "m5": 23.0,
    "h1": 138.0,
    "h6": 1081.0,
    "h24": 4948.0
   },
   "sells": {
    "m5": 39.0,
    "h1": 141.0,
    "h6": 1098.0,
    "h24": 5412.0
   },
   "makers": {
    "m5": 51.0,
    "h1": 159.0,
    "h6": 503.0,
    "h24": 1244.0
   },
   "liquidity": 407710.86,
   "marketCap": 27572650.0,
   "fdv": 27572650.0,
   "createdAt": 1792637455000.0,
   "holders": null
  },
  {
   "rank": 25.0,
   "pool": "0x4cd38b038513dc5a73fba933dafa39f7233c44fa",
   "url": "https://dexscreener.com/base/0x4cd38b038513dc5a73fba933dafa39f7233c44fa",
   "dex": "Aero Slipstream (Base)",
   "token": "0xb3b32f9f8827d4634fe7d973fa1034ec9fddb3b3",
   "name": "B3",
   "symbol": "B3",
   "quote": "WETH",
   "logo": "https://coin-images.coingecko.com/coins/images/54287/large/B3.png?1739001374",
   "price": 0.0005943,
   "change": {
    "m5": 0.43,
    "h1": 0.12,
    "h6": 2.45,
    "h24": -2.1
   },
   "volume": {
    "m5": 666.34,
    "h1": 944.35,
    "h6": 25016.95,
    "h24": 294178.68
   },
   "buys": {
    "m5": 11.0,
    "h1": 22.0,
    "h6": 86.0,
    "h24": 684.0
   },
   "sells": {
    "m5": 0.0,
    "h1": 0.0,
    "h6": 38.0,
    "h24": 448.0
   },
   "makers": {
    "m5": 7.0,
    "h1": 14.0,
    "h6": 51.0,
    "h24": 200.0
   },
   "liquidity": 627587.59,
   "marketCap": 27597795.0,
   "fdv": 59437536.0,
   "createdAt": 1792640447000.0,
   "holders": null
  },
  {
   "rank": 26.0,
   "pool": "0xc85d5cb72d1aad6f152a8decad228ae4a59ac9b3",
   "url": "https://dexscreener.com/base/0xc85d5cb72d1aad6f152a8decad228ae4a59ac9b3",
   "dex": "Aero Slipstream (Base)",
   "token": "0x3f5bf3edac59d650d8fdf9657a71f2f904a3a4ee",
   "name": "Aero",
   "symbol": "AERO",
   "quote": "WETH",
   "logo": "https://coin-images.coingecko.com/coins/images/102179737/large/aero-token.png?1792751076",
   "price": 0.6062,
   "change": {
    "m5": 0.54,
    "h1": 0.95,
    "h6": 1.96,
    "h24": -2.4
   },
   "volume": {
    "m5": 42351.84,
    "h1": 379286.55,
    "h6": 1552989.95,
    "h24": 7605568.65
   },
   "buys": {
    "m5": 67.0,
    "h1": 185.0,
    "h6": 459.0,
    "h24": 1616.0
   },
   "sells": {
    "m5": 13.0,
    "h1": 122.0,
    "h6": 800.0,
    "h24": 2770.0
   },
   "makers": {
    "m5": 21.0,
    "h1": 125.0,
    "h6": 392.0,
    "h24": 981.0
   },
   "liquidity": 3258728.41,
   "marketCap": 1293248453.0,
   "fdv": 1293248453.0,
   "createdAt": 1792637455000.0,
   "holders": null
  },
  {
   "rank": 27.0,
   "pool": "0xec33256bf1ded407a57fd3c1965e7556e42ac14db09bc4e6fef57d5e2eb0b0b9",
   "url": "https://dexscreener.com/base/0xec33256bf1ded407a57fd3c1965e7556e42ac14db09bc4e6fef57d5e2eb0b0b9",
   "dex": "Uniswap V4 (Base)",
   "token": "0x5f980dcfc4c0fa3911554cf5ab288ed0eb13dba3",
   "name": "gitlawb",
   "symbol": "GITLAWB",
   "quote": "WETH",
   "logo": "https://coin-images.coingecko.com/coins/images/102172941/large/b16bfbf1-8384-43fc-9797-88fba91ddca5.png?1776736251",
   "price": 7.449e-06,
   "change": {
    "m5": -0.29,
    "h1": -1.89,
    "h6": -4.13,
    "h24": -14.67
   },
   "volume": {
    "m5": 299.03,
    "h1": 1609.84,
    "h6": 12272.49,
    "h24": 62863.93
   },
   "buys": {
    "m5": 0.0,
    "h1": 7.0,
    "h6": 143.0,
    "h24": 538.0
   },
   "sells": {
    "m5": 2.0,
    "h1": 7.0,
    "h6": 53.0,
    "h24": 200.0
   },
   "makers": {
    "m5": 2.0,
    "h1": 12.0,
    "h6": 45.0,
    "h24": 185.0
   },
   "liquidity": 245486.84,
   "marketCap": 737803.0,
   "fdv": 737803.0,
   "createdAt": 1773194407000.0,
   "holders": null
  },
  {
   "rank": 28.0,
   "pool": "0x16c70f04c3080a127486cdf5a4c33c066bbf47c3",
   "url": "https://dexscreener.com/base/0x16c70f04c3080a127486cdf5a4c33c066bbf47c3",
   "dex": "Aero Slipstream (Base)",
   "token": "0xb2000000000000000000002d0ba3164cc74f58b7",
   "name": "Alphabet Inc.",
   "symbol": "GOOGLC",
   "quote": "USDC",
   "logo": "https://coin-images.coingecko.com/coins/images/102175598/large/goog_200x200.png?1787068802",
   "price": 280.067,
   "change": {
    "m5": 0.11,
    "h1": 0.12,
    "h6": 0.32,
    "h24": -0.99
   },
   "volume": {
    "m5": 22555.35,
    "h1": 393444.94,
    "h6": 2042778.39,
    "h24": 8508487.35
   },
   "buys": {
    "m5": 13.0,
    "h1": 83.0,
    "h6": 554.0,
    "h24": 2335.0
   },
   "sells": {
    "m5": 1.0,
    "h1": 66.0,
    "h6": 385.0,
    "h24": 2547.0
   },
   "makers": {
    "m5": 16.0,
    "h1": 104.0,
    "h6": 449.0,
    "h24": 1096.0
   },
   "liquidity": 1596174.55,
   "marketCap": 8349952.0,
   "fdv": 8349952.0,
   "createdAt": 1792637511000.0,
   "holders": null
  },
  {
   "rank": 29.0,
   "pool": "0xf1cacd7e005b9337c58aae77bc88d93c635cdf4d",
   "url": "https://dexscreener.com/base/0xf1cacd7e005b9337c58aae77bc88d93c635cdf4d",
   "dex": "Pancakeswap V3 (Base)",
   "token": "0x853a7c99227499dba9db8c3a02aa691afdebf841",
   "name": "Play",
   "symbol": "PLAY",
   "quote": "USDC",
   "logo": "https://coin-images.coingecko.com/coins/images/67765/large/plays.jpg?1753786347",
   "price": 0.01287,
   "change": {
    "m5": 0.15,
    "h1": 0.16,
    "h6": 0.84,
    "h24": -5.89
   },
   "volume": {
    "m5": 6175.29,
    "h1": 102325.54,
    "h6": 333727.2,
    "h24": 1065990.91
   },
   "buys": {
    "m5": 36.0,
    "h1": 595.0,
    "h6": 1998.0,
    "h24": 5905.0
   },
   "sells": {
    "m5": 38.0,
    "h1": 618.0,
    "h6": 1925.0,
    "h24": 5291.0
   },
   "makers": {
    "m5": 37.0,
    "h1": 179.0,
    "h6": 452.0,
    "h24": 1204.0
   },
   "liquidity": 274742.71,
   "marketCap": 4809106.0,
   "fdv": 51503146.0,
   "createdAt": 1777888511000.0,
   "holders": null
  },
  {
   "rank": 30.0,
   "pool": "0x85f1aa3a70fedd1c52705c15baed143e675cd626",
   "url": "https://dexscreener.com/base/0x85f1aa3a70fedd1c52705c15baed143e675cd626",
   "dex": "Aerodrome (Base)",
   "token": "0x9b5e262cf9bb04869ab40b19af91d2dc85761722",
   "name": "Nock",
   "symbol": "NOCK",
   "quote": "USDC",
   "logo": "https://coin-images.coingecko.com/coins/images/68474/large/GrCcG9N9_400x400.jpg?1755845184",
   "price": 0.01261,
   "change": {
    "m5": 0.0,
    "h1": 0.4,
    "h6": 1.12,
    "h24": -3.52
   },
   "volume": {
    "m5": 1.25,
    "h1": 7847.45,
    "h6": 24249.91,
    "h24": 320913.61
   },
   "buys": {
    "m5": 0.0,
    "h1": 13.0,
    "h6": 51.0,
    "h24": 450.0
   },
   "sells": {
    "m5": 1.0,
    "h1": 21.0,
    "h6": 41.0,
    "h24": 321.0
   },
   "makers": {
    "m5": 2.0,
    "h1": 28.0,
    "h6": 62.0,
    "h24": 343.0
   },
   "liquidity": 888695.54,
   "marketCap": 29944315.0,
   "fdv": 20152679.0,
   "createdAt": 1766440365000.0,
   "holders": null
  },
  {
   "rank": 31.0,
   "pool": "0xf5fcb9cdafce67d50afef298f88e709d2b946ba6",
   "url": "https://dexscreener.com/base/0xf5fcb9cdafce67d50afef298f88e709d2b946ba6",
   "dex": "Aero Slipstream (Base)",
   "token": "0xb200000000000000000000c2e324d24d7eecd1fb",
   "name": "Apple Inc.",
   "symbol": "AAPL",
   "quote": "USDC",
   "logo": "https://coin-images.coingecko.com/coins/images/102175597/large/aapl_200x200.png?1787068801",
   "price": 325.6,
   "change": {
    "m5": -0.09,
    "h1": 0.2,
    "h6": -1.19,
    "h24": -5.45
   },
   "volume": {
    "m5": 22836.14,
    "h1": 271027.5,
    "h6": 982990.8,
    "h24": 5289924.42
   },
   "buys": {
    "m5": 15.0,
    "h1": 168.0,
    "h6": 545.0,
    "h24": 2368.0
   },
   "sells": {
    "m5": 32.0,
    "h1": 144.0,
    "h6": 636.0,
    "h24": 2603.0
   },
   "makers": {
    "m5": 32.0,
    "h1": 198.0,
    "h6": 423.0,
    "h24": 930.0
   },
   "liquidity": 528877.91,
   "marketCap": 2325666.0,
   "fdv": 2325666.0,
   "createdAt": 1792637659000.0,
   "holders": null
  },
  {
   "rank": 32.0,
   "pool": "0x880db7dda4407d99508574e680d067d1164b3cfe",
   "url": "https://dexscreener.com/base/0x880db7dda4407d99508574e680d067d1164b3cfe",
   "dex": "Aero Slipstream (Base)",
   "token": "0xb2000000000000000000007b9fcbd005511acbd5",
   "name": "Space Exploration Technologies Corp.",
   "symbol": "SPCXC",
   "quote": "USDC",
   "logo": "https://coin-images.coingecko.com/coins/images/102178284/large/spcx-200.png?1789234077",
   "price": 137.2,
   "change": {
    "m5": 0.09,
    "h1": -0.19,
    "h6": 0.38,
    "h24": 0.08
   },
   "volume": {
    "m5": 30775.35,
    "h1": 400736.36,
    "h6": 2732806.13,
    "h24": 9608210.35
   },
   "buys": {
    "m5": 20.0,
    "h1": 162.0,
    "h6": 874.0,
    "h24": 3857.0
   },
   "sells": {
    "m5": 12.0,
    "h1": 166.0,
    "h6": 808.0,
    "h24": 3935.0
   },
   "makers": {
    "m5": 35.0,
    "h1": 200.0,
    "h6": 456.0,
    "h24": 824.0
   },
   "liquidity": 728471.74,
   "marketCap": 2302504.0,
   "fdv": 2302504.0,
   "createdAt": 1792637435000.0,
   "holders": null
  },
  {
   "rank": 33.0,
   "pool": "0x17a3ad8c74c4947005afeda9965305ae2eb2518a",
   "url": "https://dexscreener.com/base/0x17a3ad8c74c4947005afeda9965305ae2eb2518a",
   "dex": "Uniswap V2 (Base)",
   "token": "0xb1a03eda10342529bbf8eb700a06c60441fef25d",
   "name": "Mister Miggles",
   "symbol": "MIGGLES",
   "quote": "WETH",
   "logo": "https://coin-images.coingecko.com/coins/images/39251/large/New_LOGO.png?1734294728",
   "price": 0.001225,
   "change": {
    "m5": 0.0,
    "h1": 0.1,
    "h6": 0.48,
    "h24": -2.42
   },
   "volume": {
    "m5": 0.0,
    "h1": 125.75,
    "h6": 877.3,
    "h24": 2013.47
   },
   "buys": {
    "m5": 0.0,
    "h1": 2.0,
    "h6": 7.0,
    "h24": 17.0
   },
   "sells": {
    "m5": 0.0,
    "h1": 0.0,
    "h6": 4.0,
    "h24": 41.0
   },
   "makers": {
    "m5": 0.0,
    "h1": 2.0,
    "h6": 11.0,
    "h24": 42.0
   },
   "liquidity": 322942.34,
   "marketCap": 1174555.0,
   "fdv": 1174555.0,
   "createdAt": 1721147933000.0,
   "holders": null
  },
  {
   "rank": 34.0,
   "pool": "0xb8e3840b850cd5e2d8229e54a04c3a10b653d072870bbfb26847d237fc655a37",
   "url": "https://dexscreener.com/base/0xb8e3840b850cd5e2d8229e54a04c3a10b653d072870bbfb26847d237fc655a37",
   "dex": "Uniswap V4 (Base)",
   "token": "0xa53887f7e7c1bf5010b8627f1c1ba94fe7a5d6e0",
   "name": "Rainbow",
   "symbol": "RNBW",
   "quote": "USDC",
   "logo": "https://coin-images.coingecko.com/coins/images/69445/large/RNBW-200px.png?1770053251",
   "price": 0.01749,
   "change": {
    "m5": 0.0,
    "h1": 0.28,
    "h6": 0.43,
    "h24": -1.45
   },
   "volume": {
    "m5": 0.0,
    "h1": 340.56,
    "h6": 4633.0,
    "h24": 32706.53
   },
   "buys": {
    "m5": 0.0,
    "h1": 3.0,
    "h6": 31.0,
    "h24": 189.0
   },
   "sells": {
    "m5": 0.0,
    "h1": 1.0,
    "h6": 8.0,
    "h24": 114.0
   },
   "makers": {
    "m5": 0.0,
    "h1": 4.0,
    "h6": 27.0,
    "h24": 106.0
   },
   "liquidity": 152399.83,
   "marketCap": 17488768.0,
   "fdv": 17488768.0,
   "createdAt": 1770307249000.0,
   "holders": null
  }
 ]
};
