import pandas as pd
import random
df=pd.read_csv("ordersold2.csv",index_col=False)
p=pd.read_csv("products.csv",index_col=False)

l=len(p)

def random_pids(c):
    num=random.randint(1,4)
    ids=random.sample(range(1,l+1),num)
    return ",".join(map(str,ids))

df["product_ids"]=df["product_ids"].apply(random_pids)

df.to_csv("orders.csv",index=False)