/* ----------------------------------------------------------------------------
 * This file was automatically generated by SWIG (http://www.swig.org).
 * Version 4.0.2
 *
 * Do not make changes to this file unless you know what you are doing--modify
 * the SWIG interface file instead.
 * ----------------------------------------------------------------------------- */

package btllib;

public class SeqReaderFastaModule {
  private transient long swigCPtr;
  protected transient boolean swigCMemOwn;

  protected SeqReaderFastaModule(long cPtr, boolean cMemoryOwn) {
    swigCMemOwn = cMemoryOwn;
    swigCPtr = cPtr;
  }

  protected static long getCPtr(SeqReaderFastaModule obj) {
    return (obj == null) ? 0 : obj.swigCPtr;
  }

  @SuppressWarnings("deprecation")
  protected void finalize() {
    delete();
  }

  public synchronized void delete() {
    if (swigCPtr != 0) {
      if (swigCMemOwn) {
        swigCMemOwn = false;
        btllibJNI.delete_SeqReaderFastaModule(swigCPtr);
      }
      swigCPtr = 0;
    }
  }

  public SeqReaderFastaModule() {
    this(btllibJNI.new_SeqReaderFastaModule(), true);
  }

}
