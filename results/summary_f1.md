Lite dev sweep (n=300):
  hybrid: θ=0.2:F1=22.2  θ=0.3:F1=22.3  θ=0.4:F1=22.6  θ=0.5:F1=23.7  θ=0.6:F1=26.5  θ=0.7:F1=29.9  θ=0.8:F1=34.3  θ=0.9:F1=37.9
  -> best θ=0.9 (P=33.3 R=49.3 F1=37.9)
  bm25: θ=0.2:F1=16.1  θ=0.3:F1=16.1  θ=0.4:F1=16.1  θ=0.5:F1=16.5  θ=0.6:F1=17.3  θ=0.7:F1=19.3  θ=0.8:F1=22.7  θ=0.9:F1=26.4
  -> best θ=0.9 (P=23.1 R=36.0 F1=26.4)

Verified test (n=500), θ fixed from Lite:
  hybrid  θ=0.9  Prec=32.6  Rec=44.6  F1=35.2
  bm25    θ=0.9  Prec=17.2  Rec=25.4  F1=18.8

Reference (CodeScout paper, Table 3, file-level F1 on Verified): Agentless 35.4, LocAgent 44.2, CodeScout-1.7B 55.5, CodeScout-4B 68.5, CodeScout-14B 68.6, RepoNavigator-32B 67.8, Claude-Sonnet-4.5 (best scaffold) 82.0
