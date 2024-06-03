import pandas as pd
import numpy as np
from olist.utils import haversine_distance
from olist.data import Olist
from datetime import timedelta

class Order:
    '''
    DataFrames containing all orders as index,
    and various properties of these orders as columns
    '''
    def __init__(self):
        # Assign an attribute ".data" to all new instances of Order
        self.data = Olist().get_data()

    def get_wait_time(self, is_delivered=True):
        """
        Returns a DataFrame with:
        [order_id, wait_time, expected_wait_time, delay_vs_expected, order_status]
        and filters out non-delivered orders unless specified
        """
        olist = Olist()
        data = olist.get_data()
        orders=data['orders']
        # Hint: Within this instance method, you have access to the instance of the class Order in the variable self, as well as all its attributes
        orders['order_purchase_timestamp']=pd.to_datetime(orders['order_purchase_timestamp'])
        orders['order_delivered_customer_date']=pd.to_datetime(orders['order_delivered_customer_date'])
        orders['order_estimated_delivery_date']=pd.to_datetime(orders['order_estimated_delivery_date'])
        orders['wait_time']=orders['order_delivered_customer_date'] - orders['order_purchase_timestamp']
        orders['wait_time']=orders['wait_time']/timedelta(days=1)
        orders['expected_wait_time']=(orders['order_estimated_delivery_date'] - orders['order_purchase_timestamp'])/timedelta(days=1)
        orders['delay_vs_expected'] = (orders['order_delivered_customer_date']-orders['order_estimated_delivery_date'])/timedelta(days=1)
        orders['delay_vs_expected'] = orders['delay_vs_expected'].apply(lambda x: max(x, 0.0))
        return orders[orders['order_status']=='delivered'][['order_id', 'wait_time', 'expected_wait_time', 'delay_vs_expected', 'order_status']]

    def get_review_score(self):
        """
        Returns a DataFrame with:
        order_id, dim_is_five_star, dim_is_one_star, review_score
        """
        olist = Olist()
        data = olist.get_data()
        reviews=data['order_reviews']
        reviews['dim_is_five_star'] = reviews['review_score'].apply(lambda x: 1 if x==5 else 0)
        reviews['dim_is_one_star']=reviews['review_score'].apply(lambda x: 1 if x==1 else 0)
        return reviews[['order_id','dim_is_five_star', 'dim_is_one_star', 'review_score']]


    def get_number_products(self):
        """
        Returns a DataFrame with:
        order_id, number_of_products
        """
        olist = Olist()
        data = olist.get_data()
        order_items=data['order_items']
        order_items = order_items.groupby(by='order_id').count().copy()
        order_items.reset_index(inplace=True)
        orders=order_items[['order_id','order_item_id']]
        orders=orders.rename(columns={"order_id": "order_id", "order_item_id": "number_of_products"})
        return orders

    def get_number_sellers(self):
        """
        Returns a DataFrame with:
        order_id, number_of_sellers
        """
        olist = Olist()
        data = olist.get_data()
        order_items=data['order_items']
        sellers=data['sellers']
        merged_data=pd.merge(order_items, sellers, how='inner', on='seller_id')
        sellers_order=merged_data.groupby('order_id')[['seller_id']].nunique()
        sellers_order.reset_index(inplace=True)
        sellers_order=sellers_order.rename(columns={"order_id": "order_id", "seller_id": "number_of_sellers"})
        return sellers_order

    def get_price_and_freight(self):
        """
        Returns a DataFrame with:
        order_id, price, freight_value
        """
        olist = Olist()
        data = olist.get_data()
        order_items=data['order_items']
        order_item=order_items.groupby('order_id')[['price','freight_value']].agg('sum','sum')
        order_item.reset_index(inplace=True)
        return order_item

    # Optional
    def get_distance_seller_customer(self):
        """
        Returns a DataFrame with:
        order_id, distance_seller_customer
        """
        data = self.data
        orders = data['orders']
        order_items = data['order_items']
        sellers = data['sellers']
        customers = data['customers']

        # Since one zip code can map to multiple (lat, lng), take the first one
        geo = data['geolocation']
        geo = geo.groupby('geolocation_zip_code_prefix',
                          as_index=False).first()

        # Merge geo_location for sellers
        sellers_mask_columns = [
            'seller_id', 'seller_zip_code_prefix', 'geolocation_lat', 'geolocation_lng'
        ]

        sellers_geo = sellers.merge(
            geo,
            how='left',
            left_on='seller_zip_code_prefix',
            right_on='geolocation_zip_code_prefix')[sellers_mask_columns]

        # Merge geo_location for customers
        customers_mask_columns = ['customer_id', 'customer_zip_code_prefix', 'geolocation_lat', 'geolocation_lng']

        customers_geo = customers.merge(
            geo,
            how='left',
            left_on='customer_zip_code_prefix',
            right_on='geolocation_zip_code_prefix')[customers_mask_columns]

        # Match customers with sellers in one table
        customers_sellers = customers.merge(orders, on='customer_id')\
            .merge(order_items, on='order_id')\
            .merge(sellers, on='seller_id')\
            [['order_id', 'customer_id','customer_zip_code_prefix', 'seller_id', 'seller_zip_code_prefix']]

        # Add the geoloc
        matching_geo = customers_sellers.merge(sellers_geo,
                                            on='seller_id')\
            .merge(customers_geo,
                   on='customer_id',
                   suffixes=('_seller',
                             '_customer'))
        # Remove na()
        matching_geo = matching_geo.dropna()

        matching_geo.loc[:, 'distance_seller_customer'] =\
            matching_geo.apply(lambda row:
                               haversine_distance(row['geolocation_lng_seller'],
                                                  row['geolocation_lat_seller'],
                                                  row['geolocation_lng_customer'],
                                                  row['geolocation_lat_customer']),
                               axis=1)
        # Since an order can have multiple sellers,
        # return the average of the distance per order
        order_distance =\
            matching_geo.groupby('order_id',
                                 as_index=False).agg({'distance_seller_customer':
                                                      'mean'})

        return order_distance
    def get_training_data(self,is_delivered=True,with_distance_seller_customer=False):
        training= pd.merge(self.get_wait_time(),self.get_review_score(), how='inner',on='order_id').merge(self.get_number_products(), how='inner',on='order_id').merge(self.get_number_sellers(), how='inner',on='order_id').merge(self.get_price_and_freight(), how='inner',on='order_id')
        if with_distance_seller_customer:
            training = training.merge(
                self.get_distance_seller_customer(), on='order_id')
        return training.dropna()

    """Returns a clean DataFrame (without NaN), with the all following columns:
        ['order_id', 'wait_time', 'expected_wait_time', 'delay_vs_expected',
        'order_status', 'dim_is_five_star', 'dim_is_one_star', 'review_score',
        'number_of_products', 'number_of_sellers', 'price', 'freight_value',
        'distance_seller_customer']
        """
