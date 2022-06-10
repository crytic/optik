contract Time {
    uint start;
    uint marked;

    constructor() public {
        start  = block.timestamp;
        marked = block.timestamp;
    }

    function mark() public {
        marked = block.timestamp;
    }

    function check_marked_time() public returns (int) {
        if (start + 69 minutes == marked)
            return -1; // test::coverage
        else {
            if (marked > start + 2 days)
                if (marked < start + 3 days)
                    return -2; // test::coverage
                else
                    return 3; // test::coverage
            else
                if (marked == start + 78 minutes)
                    return -4; // test::coverage
                else
                    return -5; // test::coverage
        }
    }

    function check_current_time() public returns (bool) {
        if (block.timestamp > start + 2 weeks)
            return true; // test::coverage
        else
            return false; // test::coverage
    }

}