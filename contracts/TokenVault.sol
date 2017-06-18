import "./StandardToken.sol";
import "zeppelin/contracts/ownership/Ownable.sol";

/**
 * Hold tokens for a group investor of investors until the unlock date.
 *
 * After the unlock date the investor can claim their tokens.
 *
 * Steps
 *
 * - Prepare a spreadsheet for token allocation
 * - Deploy this contract, with the sum to tokens to be distributed, from the owner account
 * - Call setInvestor for all investors from the owner account using a local script and CSV input
 * - Call lock from the owner account
 * - Move tokensToBeAllocated in this contract usign StandardToken.transfer()
 * - Wait until the freeze period is over
 * - After the freeze time is over investors can call claim() from their address to get their tokens
 *
 */
contract TokenVault is Ownable {

  /** How many investors we have now */
  uint public investorCount;

  /** Sum from the spreadsheet how much tokens we should get on the contract. If the sum does not match at the time of the lock the vault is faulty and must be recreated.*/
  uint public tokensToBeAllocated;

  /** How many tokens investors have claimed so far */
  uint public totalClaimed;

  /** How many tokens our internal book keeping tells us to have at the time of lock() when all investor data has been loaded */
  uint public tokensAllocatedTotal;

  /** How much we have allocated to the investors invested */
  mapping(address => uint) public balances;

  /** How many tokens investors have claimed */
  mapping(address => uint) public claimed;

  /** When our claim freeze is over (UNIX timestamp) */
  uint public freezeEndsAt;

  /** When this vault was locked (UNIX timestamp) */
  uint public lockedAt;

  /** We can also define our own token, which will override the ICO one ***/
  StandardToken public token;

  /** What is our current state.
   *
   * Loading: Investor data is being loaded and contract not yet locked
   * Holding: Holding tokens for investors
   * Distributing: Freeze time is over, investors can claim their tokens
   */
  enum State{Unknown, Loading, Holding, Distributing}

  /** We allocated tokens for investor */
  event Allocated(address investor, uint value);

  /** We distributed tokens to an investor */
  event Distributed(address investors, uint count);

  event Locked();

  /**
   * Create presale contract where lock up period is given days
   *
   * @param _owner Who can load investor data and lock
   * @param _freezeEndsAt UNIX timestamp when the vault unlocks
   * @param _token Token contract address we are distributing
   * @param _tokensToBeAllocated Total number of tokens this vault will hold - including decimal multiplcation
   *
   */
  function TokenVault(address _owner, uint _freezeEndsAt, StandardToken _token, uint _tokensToBeAllocated) {

    owner = _owner;

    // Invalid owenr
    if(owner == 0) {
      throw;
    }

    token = _token;

    // Check the address looks like a token contract
    if(!token.isToken()) {
      throw;
    }

    // Give argument
    if(_freezeEndsAt == 0) {
      throw;
    }

    freezeEndsAt = _freezeEndsAt;
    tokensToBeAllocated = _tokensToBeAllocated;
  }

  /**
   * Add a presale participatin allocation.
   */
  function setInvestor(address investor, uint amount) public onlyOwner {

    if(lockedAt > 0) {
      // Cannot add new investors after the vault is locked
      throw;
    }

    if(amount == 0) throw; // No empty buys

    // Don't allow reset
    bool existing = balances[investor] > 0;
    if(existing) {
      throw;
    }

    balances[investor] = amount;

    investorCount++;

    tokensAllocatedTotal += amount;

    Allocated(investor, amount);
  }

  /**
   * Lock the vault.
   *
   *
   * - All balances have been loaded in correctly
   * - Tokens are transferred on this vault correctly
   *
   * Checks are in place to prevent creating a vault that is locked with incorrect token balances.
   *
   */
  function lock() onlyOwner {

    if(lockedAt > 0) {
      throw; // Already locked
    }

    // Spreadsheet sum does not match to what we have loaded to the investor data
    if(tokensAllocatedTotal != tokensToBeAllocated) {
      throw;
    }

    // Do not lock the vault if the given tokens on this contract
    //
    if(token.balanceOf(address(this)) != tokensAllocatedTotal) {
      throw;
    }

    lockedAt = now;

    Locked();
  }

  /**
   * In the case locking failed, then allow the owner to reclaim the tokens on the contract.
   */
  function recoverFailedLock() onlyOwner {
    if(lockedAt > 0) {
      throw;
    }

    // Transfer all tokens on this contract back to the owner
    token.transfer(owner, token.balanceOf(address(this)));
  }

  /**
   * Get the current balance of tokens in the vault.
   */
  function getBalance() public constant returns (uint howManyTokensCurrentlyInVault) {
    return token.balanceOf(address(this));
  }

  /**
   * Claim N bought tokens to the investor as the msg sender.
   *
   */
  function claim() {

    address investor = msg.sender;

    if(lockedAt == 0) {
      throw; // We were never locked
    }

    if(now < freezeEndsAt) {
      throw; // Trying to claim early
    }

    if(balances[investor] == 0) {
      // Not our investor
      throw;
    }

    if(claimed[investor] > 0) {
      throw; // Already claimed
    }

    uint amount = balances[investor];

    claimed[investor] = amount;

    totalClaimed += amount;

    token.transfer(investor, amount);

    Distributed(investor, amount);
  }

  /**
   * Resolve the contract umambigious state.
   */
  function getState() public returns(State) {
    if(lockedAt == 0) {
      return State.Loading;
    } else if(now > freezeEndsAt) {
      return State.Distributing;
    } else {
      return State.Holding;
    }
  }

}
