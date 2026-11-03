#import <AdSupport/AdSupport.h>

NSString *AdvertisingId(void) {
    return [[[ASIdentifierManager sharedManager] advertisingIdentifier] UUIDString];
}
