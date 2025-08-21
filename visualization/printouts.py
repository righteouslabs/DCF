import logging

logger = logging.getLogger(__name__)

def prettyprint(dcfs, years):
    '''
    Pretty print-out results of a DCF query.
    Handles formatting for all output variatisons.
    '''
    if years > 1:
        for k, v in dcfs.items():
            logger.info(f'DCF Results - Ticker: {k}')
            if len(dcfs[k].keys()) > 1:
                for yr, dcf in v.items():
                    logger.info(f'  Date: {yr}, Value: {dcf}')
    else:
        for k, v in dcfs.items():
            logger.info(f'DCF Results - Ticker: {k}, Value: {v}')
